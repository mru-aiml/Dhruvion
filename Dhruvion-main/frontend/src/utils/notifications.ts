export interface Notification { id: string; text: string; read: boolean; link?: string; }

export function pushNotification(text: string, link?: string) {
  try {
    const raw = localStorage.getItem("dhruvion.notifications");
    const list: Notification[] = raw ? JSON.parse(raw) : [];
    list.unshift({ id: Date.now().toString(), text, read: false, link });
    localStorage.setItem("dhruvion.notifications", JSON.stringify(list.slice(0, 50)));
    window.dispatchEvent(new Event("dhruvion:notifications"));
  } catch { /* ignore */ }
}