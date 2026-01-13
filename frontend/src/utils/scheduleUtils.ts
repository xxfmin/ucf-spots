// ============================================
// Schedule Processing Utilities
// ============================================
// Uses America/New_York timezone for UCF
// ============================================

import moment from "moment-timezone";
import { RoomScheduleBlock, HourlyScheduleBlock, BlockSection } from "@/types";

/** UCF timezone */
const TIMEZONE = "America/New_York";

/**
 * Processes raw schedule data into hourly blocks with sections
 * Used for rendering the hourly schedule view in the UI
 *
 * @param scheduleData - The raw schedule data from the API
 * @returns An array of hourly blocks with sections
 */
export function processScheduleIntoHourlyBlocks(
  scheduleData: RoomScheduleBlock[]
): HourlyScheduleBlock[] {
  if (!scheduleData || scheduleData.length === 0) {
    return [];
  }

  const hourlyBlocks: HourlyScheduleBlock[] = [];

  const firstBlock = scheduleData[0];
  const lastBlock = scheduleData[scheduleData.length - 1];

  const firstStartTime = moment.tz(`1970-01-01T${firstBlock.start}`, TIMEZONE);
  const lastEndTime = moment.tz(`1970-01-01T${lastBlock.end}`, TIMEZONE);

  // Special handling for the first block - it can start at any time
  let currentTime = firstStartTime.clone();

  // For the first block, keep its original start time
  // but round the end time to the next hour boundary if it crosses an hour
  let firstBlockEndTime = currentTime.clone();
  if (firstBlockEndTime.minutes() > 0 || firstBlockEndTime.seconds() > 0) {
    firstBlockEndTime.add(1, "hour").startOf("hour");
  } else {
    firstBlockEndTime.add(1, "hour");
  }

  // Make sure we don't exceed the last end time
  if (firstBlockEndTime.isAfter(lastEndTime)) {
    firstBlockEndTime = lastEndTime.clone();
  }

  const firstHourlyBlock = createHourlyBlock(
    currentTime,
    firstBlockEndTime,
    scheduleData
  );
  hourlyBlocks.push(firstHourlyBlock);

  currentTime = firstBlockEndTime.clone();

  // Create standard 1-hour blocks until we reach the last end time
  while (currentTime.isBefore(lastEndTime)) {
    const blockEndTime = currentTime.clone().add(1, "hour");

    // Make sure we don't exceed the last end time
    const endTime = blockEndTime.isAfter(lastEndTime)
      ? lastEndTime.clone()
      : blockEndTime;

    const hourlyBlock = createHourlyBlock(currentTime, endTime, scheduleData);
    hourlyBlocks.push(hourlyBlock);

    currentTime = endTime.clone();
  }

  return hourlyBlocks;
}

/**
 * Creates a single hourly block with sections based on the schedule data
 */
function createHourlyBlock(
  startTime: moment.Moment,
  endTime: moment.Moment,
  scheduleData: RoomScheduleBlock[]
): HourlyScheduleBlock {
  const sections: BlockSection[] = [];

  const blockStartStr = startTime.format("HH:mm:ss");
  const blockEndStr = endTime.format("HH:mm:ss");

  // Find all schedule blocks that overlap with this hourly block
  const overlappingBlocks = scheduleData.filter((block) => {
    const blockStart = moment.tz(`1970-01-01T${block.start}`, TIMEZONE);
    const blockEnd = moment.tz(`1970-01-01T${block.end}`, TIMEZONE);

    // A block overlaps if it starts before the hourly block ends AND ends after the hourly block starts
    return blockStart.isBefore(endTime) && blockEnd.isAfter(startTime);
  });

  if (overlappingBlocks.length === 0) {
    // If no overlapping blocks, create a single available section
    sections.push({
      start: blockStartStr,
      end: blockEndStr,
      status: "available",
      details: null,
    });
  } else {
    let currentSectionStart = startTime.clone();

    // Sort overlapping blocks by start time
    overlappingBlocks.sort((a, b) => {
      const aStart = moment.tz(`1970-01-01T${a.start}`, TIMEZONE);
      const bStart = moment.tz(`1970-01-01T${b.start}`, TIMEZONE);
      return aStart.diff(bStart);
    });

    for (const block of overlappingBlocks) {
      const blockStart = moment.tz(`1970-01-01T${block.start}`, TIMEZONE);
      const blockEnd = moment.tz(`1970-01-01T${block.end}`, TIMEZONE);

      // Adjust block times to be within the hourly block
      const adjustedStart = blockStart.isBefore(startTime)
        ? startTime.clone()
        : blockStart.clone();
      const adjustedEnd = blockEnd.isAfter(endTime)
        ? endTime.clone()
        : blockEnd.clone();

      // If there's a gap before this block, add an available section
      if (adjustedStart.isAfter(currentSectionStart)) {
        sections.push({
          start: currentSectionStart.format("HH:mm:ss"),
          end: adjustedStart.format("HH:mm:ss"),
          status: "available",
          details: null,
        });
      }

      // Add the current block as a section
      sections.push({
        start: adjustedStart.format("HH:mm:ss"),
        end: adjustedEnd.format("HH:mm:ss"),
        status: block.status,
        details: block.details,
      });

      // Update the current section start time
      currentSectionStart = adjustedEnd.clone();
    }

    // If there's remaining time after the last block, add an available section
    if (currentSectionStart.isBefore(endTime)) {
      sections.push({
        start: currentSectionStart.format("HH:mm:ss"),
        end: endTime.format("HH:mm:ss"),
        status: "available",
        details: null,
      });
    }
  }

  return {
    start: blockStartStr,
    end: blockEndStr,
    sections,
  };
}

/**
 * Calculates the total available time in a schedule
 * @param scheduleData - Array of schedule blocks
 * @returns Total available time in minutes
 */
export function calculateTotalAvailableTime(
  scheduleData: RoomScheduleBlock[]
): number {
  if (!scheduleData || scheduleData.length === 0) {
    return 0;
  }

  let totalMinutes = 0;

  for (const block of scheduleData) {
    if (block.status === "available") {
      const start = moment.tz(`1970-01-01T${block.start}`, TIMEZONE);
      const end = moment.tz(`1970-01-01T${block.end}`, TIMEZONE);
      totalMinutes += end.diff(start, "minutes");
    }
  }

  return totalMinutes;
}

/**
 * Finds the next available block from a given time
 * @param scheduleData - Array of schedule blocks
 * @param fromTime - Time to search from (HH:mm:ss format)
 * @returns The next available block, or null if none found
 */
export function findNextAvailableBlock(
  scheduleData: RoomScheduleBlock[],
  fromTime: string
): RoomScheduleBlock | null {
  if (!scheduleData || scheduleData.length === 0) {
    return null;
  }

  const fromMoment = moment.tz(`1970-01-01T${fromTime}`, TIMEZONE);

  for (const block of scheduleData) {
    if (block.status === "available") {
      const blockStart = moment.tz(`1970-01-01T${block.start}`, TIMEZONE);
      const blockEnd = moment.tz(`1970-01-01T${block.end}`, TIMEZONE);

      // Check if this block overlaps with or is after fromTime
      if (blockEnd.isAfter(fromMoment)) {
        return block;
      }
    }
  }

  return null;
}

/**
 * Gets the current block based on a given time
 * @param scheduleData - Array of schedule blocks
 * @param currentTime - Current time (HH:mm:ss format)
 * @returns The current block, or null if not within any block
 */
export function getCurrentBlock(
  scheduleData: RoomScheduleBlock[],
  currentTime: string
): RoomScheduleBlock | null {
  if (!scheduleData || scheduleData.length === 0) {
    return null;
  }

  const currentMoment = moment.tz(`1970-01-01T${currentTime}`, TIMEZONE);

  for (const block of scheduleData) {
    const blockStart = moment.tz(`1970-01-01T${block.start}`, TIMEZONE);
    const blockEnd = moment.tz(`1970-01-01T${block.end}`, TIMEZONE);

    if (
      currentMoment.isSameOrAfter(blockStart) &&
      currentMoment.isBefore(blockEnd)
    ) {
      return block;
    }
  }

  return null;
}
