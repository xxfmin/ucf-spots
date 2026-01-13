// ============================================
// Time and Date Formatting Utilities
// ============================================

/**
 * Formats a time string to 12-hour format with AM/PM
 * @param time - Time string in HH:mm or HH:mm:ss format, or undefined
 * @returns Formatted time string (e.g., "9:30 AM") or empty string if input is falsy
 */
export const formatTime = (time: string | undefined): string => {
  if (!time) return "";

  // Strip seconds if present and get HH:mm
  const timeWithoutSeconds = time.split(":").slice(0, 2).join(":");

  // Validate time format (HH:mm)
  const timeRegex = /^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$/;
  if (!timeRegex.test(timeWithoutSeconds)) {
    console.warn(
      `Invalid time format: ${time}. Expected format: HH:mm or HH:mm:ss`
    );
    return time; // Return original string if invalid
  }

  const [hours, minutes] = timeWithoutSeconds.split(":");
  const hour = parseInt(hours, 10);
  const minute = parseInt(minutes, 10);

  // Additional validation
  if (
    isNaN(hour) ||
    isNaN(minute) ||
    hour < 0 ||
    hour > 23 ||
    minute < 0 ||
    minute > 59
  ) {
    console.warn(`Invalid time values: hours=${hour}, minutes=${minute}`);
    return time;
  }

  const ampm = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;

  // Ensure minutes are always two digits
  const formattedMinutes = minutes.toString().padStart(2, "0");
  return `${hour12}:${formattedMinutes} ${ampm}`;
};

/**
 * Formats a duration in minutes to a human-readable string
 * @param minutes - Duration in minutes, or undefined
 * @returns Formatted duration string (e.g., "2h 30m") or empty string if input is falsy
 */
export const formatDuration = (minutes: number | undefined): string => {
  if (!minutes || minutes <= 0) return "";

  if (minutes < 60) {
    return `${Math.floor(minutes)} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = Math.floor(minutes % 60);

  if (remainingMinutes > 0) {
    return `${hours}h ${remainingMinutes}m`;
  }

  return `${hours}h`;
};

/**
 * Formats a time range
 * @param start - Start time in HH:mm or HH:mm:ss format
 * @param end - End time in HH:mm or HH:mm:ss format
 * @returns Formatted time range (e.g., "9:30 AM - 10:45 AM")
 */
export const formatTimeRange = (
  start: string | undefined,
  end: string | undefined
): string => {
  if (!start || !end) return "";
  return `${formatTime(start)} - ${formatTime(end)}`;
};

/**
 * Calculates the duration in minutes between two times
 * @param start - Start time in HH:mm or HH:mm:ss format
 * @param end - End time in HH:mm or HH:mm:ss format
 * @returns Duration in minutes, or 0 if invalid
 */
export const calculateDuration = (
  start: string | undefined,
  end: string | undefined
): number => {
  if (!start || !end) return 0;

  const parseTime = (time: string): number => {
    const parts = time.split(":");
    const hours = parseInt(parts[0], 10);
    const minutes = parseInt(parts[1], 10);
    return hours * 60 + minutes;
  };

  const startMinutes = parseTime(start);
  const endMinutes = parseTime(end);

  // Handle case where end is before start (shouldn't happen, but just in case)
  if (endMinutes < startMinutes) {
    return 0;
  }

  return endMinutes - startMinutes;
};

/**
 * Formats a date to a readable string
 * @param date - Date object or ISO string
 * @returns Formatted date string (e.g., "Monday, January 13, 2026")
 */
export const formatDate = (date: Date | string): string => {
  const dateObj = typeof date === "string" ? new Date(date) : date;

  return dateObj.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

/**
 * Formats a date to short format
 * @param date - Date object or ISO string
 * @returns Formatted date string (e.g., "Jan 13")
 */
export const formatDateShort = (date: Date | string): string => {
  const dateObj = typeof date === "string" ? new Date(date) : date;

  return dateObj.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
};

/**
 * Checks if a time is in the past relative to another time
 * @param time - Time to check in HH:mm or HH:mm:ss format
 * @param referenceTime - Reference time in HH:mm or HH:mm:ss format
 * @returns True if time is before referenceTime
 */
export const isTimePast = (time: string, referenceTime: string): boolean => {
  const parseTime = (t: string): number => {
    const parts = t.split(":");
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  };

  return parseTime(time) < parseTime(referenceTime);
};
