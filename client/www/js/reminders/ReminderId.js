/**
 * CANONICAL REMINDER ID UTILITIES
 * 
 * Invariants:
 * 1 reminder -> 1 canonical reminder_id (UUID string)
 * Android PendingIntent requestCode -> stable positive 31-bit integer
 */

function generateReminderId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'rem_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 9);
}

function reminderIdToRequestCode(reminderId) {
  if (typeof reminderId === 'number') {
    return Math.abs(reminderId) & 0x7FFFFFFF;
  }
  if (!reminderId) return 0;
  const str = String(reminderId);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) & 0x7FFFFFFF;
}

if (typeof window !== 'undefined') {
  window.ReminderId = {
    generateReminderId,
    reminderIdToRequestCode
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    generateReminderId,
    reminderIdToRequestCode
  };
}
