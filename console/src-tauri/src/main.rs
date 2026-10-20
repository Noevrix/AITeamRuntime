#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::{mpsc, Mutex},
    time::Duration,
};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

struct Backend(Mutex<Option<Child>>);
impl Backend {
    fn stop(&self) {
        if let Ok(mut slot) = self.0.lock() {
            if let Some(mut child) = slot.take() {
                drop(child.stdin.take());
                for _ in 0..50 {
                    if matches!(child.try_wait(), Ok(Some(_))) { return; }
                    std::thread::sleep(Duration::from_millis(100));
                }
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}
impl Drop for Backend {
    fn drop(&mut self) { self.stop(); }
}

fn main() {
    let application = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            let path = app.path().resource_dir()?.join("kernel/ai-team-kernel.exe");
            let mut command = Command::new(path);
            command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000);
            }
            let mut child = command.spawn()?;
            let stdout = child.stdout.take().ok_or("BACKEND_PIPE_MISSING")?;
            let backend = Backend(Mutex::new(Some(child)));
            let (tx, rx) = mpsc::channel();
            std::thread::spawn(move || {
                let mut line = String::new();
                let result = BufReader::new(stdout).read_line(&mut line);
                let _ = tx.send(result.map(|_| line));
            });
            let line = rx.recv_timeout(Duration::from_secs(30))
                .map_err(|_| "BACKEND_START_TIMEOUT")??;
            let ready: serde_json::Value = serde_json::from_str(&line)?;
            if ready["protocol"].as_u64() != Some(1) {
                return Err("BACKEND_START_FAILED".into());
            }
            let port = ready["port"].as_u64().filter(|p| *p > 0 && *p <= 65535)
                .ok_or("BACKEND_INVALID_PORT")?;
            let url = format!("http://127.0.0.1:{port}/");
            let origin = url.clone();
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url.parse()?))
                .title("AI Team Runtime")
                .inner_size(1440.0, 960.0)
                .min_inner_size(900.0, 640.0)
                .on_navigation(move |target| target.as_str().starts_with(&origin))
                .build()?;
            app.manage(backend);
            Ok(())
        })
        .build(tauri::generate_context!());
    match application {
        Ok(app) => app.run(|handle, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(backend) = handle.try_state::<Backend>() { backend.stop(); }
            }
        }),
        Err(_) => {
            #[cfg(windows)]
            unsafe {
                #[link(name = "user32")]
                extern "system" {
                    fn MessageBoxW(hwnd: isize, text: *const u16, title: *const u16, flags: u32) -> i32;
                }
                let text: Vec<u16> = "Local backend could not start. Check installation and AI_TEAM_DATA_ROOT. No tasks were started.\0".encode_utf16().collect();
                let title: Vec<u16> = "AI Team Runtime\0".encode_utf16().collect();
                MessageBoxW(0, text.as_ptr(), title.as_ptr(), 0x10);
            }
            std::process::exit(1);
        }
    }
}
