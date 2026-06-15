const API_URL = "https://olj4tuggm1.execute-api.us-east-1.amazonaws.com/prod";

export async function sendChat(message, sessionId) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  return res.json();
}

export async function checkStatus(executionId) {
  const res = await fetch(`${API_URL}/status?execution_id=${executionId}`);
  return res.json();
}

export async function getHistory(limit = 10) {
  const res = await fetch(`${API_URL}/history?limit=${limit}`);
  return res.json();
}

export async function getDocuments() {
  const res = await fetch(`${API_URL}/history?type=documents`);
  return res.json();
}

export async function getDashboardData(refresh = false) {
  const url = refresh
    ? `${API_URL}/dashboard-data?refresh=true`
    : `${API_URL}/dashboard-data`;
  const res = await fetch(url);
  return res.json();
}
