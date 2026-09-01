"use strict";

// Change this when FastAPI is hosted somewhere else. Keep /api/v1 in the URL.
const BACKEND_BASE_URL = "http://127.0.0.1:8000/api/v1";

const studentIdInput = document.querySelector("#student-id");
const startButton = document.querySelector("#start-call");
const hangUpButton = document.querySelector("#hang-up");
const connectionState = document.querySelector("#connection-state");
const sessionId = document.querySelector("#session-id");
const detail = document.querySelector("#detail");

let rtcClient = null;
let microphoneTrack = null;
let callIsStarting = false;

function setStatus(state, message = "") {
  connectionState.textContent = state;
  detail.textContent = message;
}

function newChannelName() {
  return `margdarshak-${crypto.randomUUID()}`;
}

function newAgoraUid() {
  const uid = new Uint32Array(1);
  crypto.getRandomValues(uid);
  return uid[0] || 1;
}

async function cleanupCall() {
  if (microphoneTrack) {
    microphoneTrack.stop();
    microphoneTrack.close();
    microphoneTrack = null;
  }
  if (rtcClient) {
    try {
      await rtcClient.leave();
    } finally {
      rtcClient.removeAllListeners();
      rtcClient = null;
    }
  }
}

async function startCall() {
  if (callIsStarting || rtcClient) return;

  const studentId = studentIdInput.value.trim();
  if (!studentId) {
    setStatus("error", "Enter the UUID of a student that exists in the database.");
    studentIdInput.focus();
    return;
  }
  if (!window.AgoraRTC) {
    setStatus("error", "Agora Web SDK did not load. Check the CDN connection.");
    return;
  }

  callIsStarting = true;
  startButton.disabled = true;
  studentIdInput.disabled = true;
  sessionId.textContent = "—";
  setStatus("starting", "Creating a backend call session…");

  try {
    const uid = newAgoraUid();
    const response = await fetch(`${BACKEND_BASE_URL}/voice/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_id: studentId,
        channel_name: newChannelName(),
        uid,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Backend returned ${response.status}: ${body}`);
    }

    const call = await response.json();
    sessionId.textContent = call.session_id;
    rtcClient = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
    rtcClient.on("connection-state-change", (currentState) => {
      setStatus(currentState.toLowerCase());
    });
    rtcClient.on("user-published", async (user, mediaType) => {
      try {
        await rtcClient.subscribe(user, mediaType);
        if (mediaType === "audio") {
          user.audioTrack.play();
          setStatus("connected", `Playing agent audio from Agora UID ${user.uid}.`);
        }
      } catch (error) {
        setStatus("error", `Could not subscribe to agent audio: ${error.message}`);
      }
    });
    rtcClient.on("user-unpublished", (user, mediaType) => {
      if (mediaType === "audio") {
        setStatus("connected", `Remote audio stopped for Agora UID ${user.uid}.`);
      }
    });

    setStatus("joining", "Joining the Agora RTC channel…");
    await rtcClient.join(call.agora_app_id, call.channel_name, call.rtc_token, uid);
    microphoneTrack = await AgoraRTC.createMicrophoneAudioTrack();
    await rtcClient.publish([microphoneTrack]);

    hangUpButton.disabled = false;
    setStatus("connected", "Microphone published; waiting for agent audio.");
  } catch (error) {
    await cleanupCall();
    setStatus("error", error instanceof Error ? error.message : String(error));
    startButton.disabled = false;
    studentIdInput.disabled = false;
  } finally {
    callIsStarting = false;
  }
}

async function hangUp() {
  hangUpButton.disabled = true;
  setStatus("disconnecting");
  try {
    await cleanupCall();
    setStatus("idle", "Call ended.");
  } catch (error) {
    setStatus("error", `Call cleanup failed: ${error.message}`);
  } finally {
    startButton.disabled = false;
    studentIdInput.disabled = false;
  }
}

startButton.addEventListener("click", startCall);
hangUpButton.addEventListener("click", hangUp);
window.addEventListener("beforeunload", () => {
  if (microphoneTrack) microphoneTrack.close();
  if (rtcClient) rtcClient.leave();
});
