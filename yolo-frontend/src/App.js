import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_URL = "http://127.0.0.1:5000";

function App() {
  const [mode, setMode] = useState(null);
  const [count, setCount] = useState(0);
  const [summary, setSummary] = useState({}); 
  const [loading, setLoading] = useState(false);
  const [videoFile, setVideoFile] = useState(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [serverStatus, setServerStatus] = useState("Checking...");
  const intervalRef = useRef(null);

  useEffect(() => { checkServer(); }, []);

  const checkServer = async () => {
    try { await fetch(`${API_URL}/`); setServerStatus("Online ✅"); }
    catch (e) { setServerStatus("Offline ❌ (Run python app.py first)"); }
  };

  const startWebcam = async () => {
    setLoading(true);
    try {
        const res = await fetch(`${API_URL}/webcam_start`);
        if (res.ok) {
            setWebcamActive(true);
            intervalRef.current = setInterval(async () => {
                try {
                    const res = await fetch(`${API_URL}/current_data`);
                    const data = await res.json();
                    setCount(data.count);
                    setSummary(data.summary);
                } catch (e) { console.error("Data fetch error", e); }
            }, 1000);
        } else { alert("Camera Start Failed!"); }
    } catch (e) { alert("Backend Error!"); }
    setLoading(false);
  };

  const stopWebcam = async () => {
    clearInterval(intervalRef.current);
    const res = await fetch(`${API_URL}/webcam_stop`);
    const data = await res.json();
    setWebcamActive(false);
    setCount(data.final_count);
    setSummary(data.final_summary);
  };

  const uploadVideo = async () => {
    if (!videoFile) return alert("Select a video first");
    setLoading(true);
    const formData = new FormData();
    formData.append('file', videoFile);

    try {
        const res = await fetch(`${API_URL}/upload_video`, { method: 'POST', body: formData });
        const data = await res.json();
        if (data.success) {
            setCount(data.total_count);
            setSummary(data.summary);
            alert("Video Processed Successfully!");
        } else { alert("Processing Failed: " + data.error); }
    } catch (e) { alert("Upload Error!"); }
    setLoading(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Object Counter</h1>
        <p style={{ color: serverStatus.includes("Online") ? "#4CAF50" : "#f44336" }}>
          Server Status: {serverStatus}
        </p>
      </header>
      <main className="main-content">
        <div className="mode-selection">
          <button className="btn" onClick={() => setMode('webcam')}>Webcam Mode</button>
          <button className="btn" onClick={() => setMode('video')}>Video Mode</button>
        </div>

        {mode === 'webcam' && (
          <div className="webcam-container">
            {webcamActive ? (
                <img src={`${API_URL}/webcam_feed`} alt="Live Feed" className="live-feed"/>
            ) : <div className="placeholder">Camera OFF</div>}
            <div className="controls">
                {!webcamActive ? 
                    <button className="btn start-btn" onClick={startWebcam} disabled={loading}>
                        {loading ? "Starting..." : "Start Camera"}
                    </button> : 
                    <button className="btn stop-btn" onClick={stopWebcam}>Stop Camera</button>
                }
            </div>
          </div>
        )}

        {mode === 'video' && (
          <div className="upload-container">
            <input type="file" accept="video/*" onChange={(e) => setVideoFile(e.target.files[0])} />
            <button className="btn upload-btn" onClick={uploadVideo} disabled={loading}>
                {loading ? "Processing..." : "Upload & Analyze"}
            </button>
          </div>
        )}

        <div className="result-section">
            <div className="total-count">
                <h2>Total: <span className="count-number">{count}</span></h2>
            </div>
            {}
            <div className="summary-list">
                <h3>Detected Objects:</h3>
                {Object.keys(summary).length > 0 ? (
                    <ul>
                        {Object.entries(summary).map(([name, quantity]) => (
                            <li key={name}>
                                <span className="obj-name">{name}</span>: <span className="obj-qty">{quantity}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p>No objects detected yet.</p>
                )}
            </div>
        </div>
      </main>
    </div>
  );
}

export default App;