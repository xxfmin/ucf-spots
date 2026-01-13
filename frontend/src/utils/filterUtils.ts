// ============================================
// Room and Building Filtering Utilities
// ============================================

import moment, { Moment } from "moment-timezone";
import { AcademicRoom, RoomStatus, Facility } from "@/types";

/** UCF timezone */
const TIMEZONE = "America/New_York";

/**
 * Criteria for filtering rooms
 */
export interface FilterCriteria {
  /** Minimum duration in minutes the room must be available */
  minDuration?: number;
  /** Room must be free until this time (HH:mm format) */
  freeUntil?: string;
  /** Room must be free by this time (HH:mm format) */
  startTime?: string;
  /** Reference time for filtering (defaults to current time) */
  now?: Moment;
  /** Only show available rooms */
  availableOnly?: boolean;
}

/**
 * Checks if a room matches the given filter criteria
 *
 * @param room - The room to check
 * @param criteria - Filter criteria to apply
 * @returns True if the room matches all criteria
 */
export const isRoomAvailable = (
  room: AcademicRoom,
  criteria: FilterCriteria
): boolean => {
  // If no criteria specified, include all rooms
  if (
    !criteria.minDuration &&
    !criteria.freeUntil &&
    !criteria.startTime &&
    !criteria.availableOnly
  ) {
    return true;
  }

  // If availableOnly is set, only consider available rooms
  if (criteria.availableOnly && room.status !== RoomStatus.AVAILABLE) {
    return false;
  }

  // For duration/time-based filters, room must be available
  if (
    (criteria.minDuration || criteria.freeUntil || criteria.startTime) &&
    room.status !== RoomStatus.AVAILABLE
  ) {
    return false;
  }

  const availableFor = room.availableFor || 0;
  const now = criteria.now ? criteria.now.clone() : moment().tz(TIMEZONE);

  // Check Start Time (room must be free by this time)
  if (criteria.startTime) {
    const [hours, minutes] = criteria.startTime.split(":").map(Number);
    const startTargetTime = now.clone().hour(hours).minute(minutes).second(0);

    // If start time is before now, it has passed
    const minutesUntilStart = startTargetTime.diff(now, "minutes");

    if (minutesUntilStart < 0) {
      return false;
    }

    // Room must be available by the start time
    if (availableFor < minutesUntilStart) {
      return false;
    }
  }

  // Check Minimum Duration
  if (criteria.minDuration && availableFor < criteria.minDuration) {
    return false;
  }

  // Check Free Until
  if (criteria.freeUntil) {
    const [hours, minutes] = criteria.freeUntil.split(":").map(Number);
    const targetTime = now.clone().hour(hours).minute(minutes).second(0);

    const diffMinutes = targetTime.diff(now, "minutes");

    if (diffMinutes < 0) {
      return false;
    }

    if (availableFor < diffMinutes) {
      return false;
    }
  }

  return true;
};

/**
 * Filters rooms in a facility based on criteria
 *
 * @param facility - The facility containing rooms
 * @param criteria - Filter criteria to apply
 * @returns Record of rooms that match the criteria
 */
export const filterRooms = (
  facility: Facility,
  criteria: FilterCriteria
): Record<string, AcademicRoom> => {
  const filteredRooms: Record<string, AcademicRoom> = {};

  for (const [roomNumber, room] of Object.entries(facility.rooms)) {
    if (isRoomAvailable(room, criteria)) {
      filteredRooms[roomNumber] = room;
    }
  }

  return filteredRooms;
};

/**
 * Counts available rooms in a facility based on criteria
 *
 * @param facility - The facility to count rooms in
 * @param criteria - Filter criteria to apply
 * @returns Number of rooms matching the criteria
 */
export const countFilteredRooms = (
  facility: Facility,
  criteria: FilterCriteria
): number => {
  return Object.values(facility.rooms).filter((room) =>
    isRoomAvailable(room, criteria)
  ).length;
};

/**
 * Filters facilities based on whether they have any matching rooms
 *
 * @param facilities - Record of facilities to filter
 * @param criteria - Filter criteria to apply
 * @returns Record of facilities that have at least one matching room
 */
export const filterFacilities = (
  facilities: Record<string, Facility>,
  criteria: FilterCriteria
): Record<string, Facility> => {
  const filteredFacilities: Record<string, Facility> = {};

  for (const [id, facility] of Object.entries(facilities)) {
    // Only include facilities that are open
    if (!facility.isOpen) {
      continue;
    }

    const filteredRooms = filterRooms(facility, criteria);

    if (Object.keys(filteredRooms).length > 0) {
      filteredFacilities[id] = {
        ...facility,
        rooms: filteredRooms,
        roomCounts: {
          available: Object.values(filteredRooms).filter(
            (r) => r.status === RoomStatus.AVAILABLE
          ).length,
          total: Object.keys(filteredRooms).length,
        },
      };
    }
  }

  return filteredFacilities;
};

/**
 * Sorts facilities by number of available rooms (descending)
 *
 * @param facilities - Record of facilities to sort
 * @returns Array of [id, facility] tuples sorted by availability
 */
export const sortFacilitiesByAvailability = (
  facilities: Record<string, Facility>
): [string, Facility][] => {
  return Object.entries(facilities).sort(([, a], [, b]) => {
    // First sort by open status (open buildings first)
    if (a.isOpen !== b.isOpen) {
      return a.isOpen ? -1 : 1;
    }

    // Then sort by number of available rooms (descending)
    return b.roomCounts.available - a.roomCounts.available;
  });
};

/**
 * Sorts rooms by status (available first, then by availableFor)
 *
 * @param rooms - Record of rooms to sort
 * @returns Array of [roomNumber, room] tuples sorted by availability
 */
export const sortRoomsByAvailability = (
  rooms: Record<string, AcademicRoom>
): [string, AcademicRoom][] => {
  const statusOrder: Record<RoomStatus, number> = {
    [RoomStatus.AVAILABLE]: 0,
    [RoomStatus.PASSING_PERIOD]: 1,
    [RoomStatus.OPENING_SOON]: 2,
    [RoomStatus.OCCUPIED]: 3,
  };

  return Object.entries(rooms).sort(([, a], [, b]) => {
    // First sort by status
    const statusDiff = statusOrder[a.status] - statusOrder[b.status];
    if (statusDiff !== 0) {
      return statusDiff;
    }

    // For available rooms, sort by availableFor (descending)
    if (a.status === RoomStatus.AVAILABLE) {
      return (b.availableFor || 0) - (a.availableFor || 0);
    }

    // For occupied rooms, sort by availableAt (ascending - sooner is better)
    if (a.status === RoomStatus.OCCUPIED && a.availableAt && b.availableAt) {
      return a.availableAt.localeCompare(b.availableAt);
    }

    return 0;
  });
};
