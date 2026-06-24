import WebSocket from "ws";
import fetch from "node-fetch";

const API_KEY = "tk_b90cd51e87b906313c22091ae3c6fc6e707d5953b4ee9566";
const USERNAME = "drnatro.taydanang";
const N8N_WEBHOOK = "http://localhost:5678/webhook/ai-livestream-comment-test";

const ws = new WebSocket(
  `wss://api.tik.tools?uniqueId=${USERNAME}&apiKey=${API_KEY}`
);

ws.on("open", () => {
  console.log("✅ Connected");
});

ws.on("message", async (raw) => {
  try {
    const msg = JSON.parse(raw.toString());

    if (msg.event !== "chat") return;

    const data = msg.data;
    if (!data?.user?.uniqueId || !data?.comment) return;

    const payload = {
      user_id: data.user.uniqueId,
      message: data.comment
    };

    console.log("💬", payload);

    await fetch(N8N_WEBHOOK, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

  } catch (err) {
    console.error("❌ error:", err.message);
  }
});