const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message");

function addMessage(text, role) {
  const item = document.createElement("p");
  item.className = `message ${role}`;
  item.textContent = `${role === "user" ? "You" : "Agent"}: ${text}`;
  chatLog.appendChild(item);
  chatLog.scrollTop = chatLog.scrollHeight;
}

addMessage("Hi! Ask me for help to see available tools.", "agent");

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  addMessage(message, "user");
  messageInput.value = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      addMessage("Request failed. Please try again.", "agent");
      return;
    }

    const data = await response.json();
    addMessage(data.reply, "agent");
  } catch (error) {
    addMessage("Unable to reach server.", "agent");
  }
});
