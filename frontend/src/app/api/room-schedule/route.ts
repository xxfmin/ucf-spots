import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import moment from "moment-timezone";
import { RoomScheduleBlock } from "@/types";

// Force dynamic rendering (no caching)
export const dynamic = "force-dynamic";

// UCF timezone
const TIMEZONE = "America/New_York";

/**
 * Validates date format (YYYY-MM-DD)
 */
function isValidDateFormat(date: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(date);
}

/**
 * Filters schedule blocks to only include blocks from the current time onwards.
 * Also truncates the first block's start time to the floored target time.
 *
 * @param fullDaySchedule - Complete day schedule from the database
 * @param targetTimeStr - Target time string (HH:mm:ss)
 * @param flooredTimeStr - Floored time string (HH:mm:ss, rounded down to nearest 10 min)
 * @returns Filtered and adjusted schedule blocks
 */
function filterScheduleFromTime(
  fullDaySchedule: RoomScheduleBlock[],
  targetTimeStr: string,
  flooredTimeStr: string
): RoomScheduleBlock[] {
  if (fullDaySchedule.length === 0) {
    return [];
  }

  let firstRelevantIndex = -1;
  let needsTruncation = false;

  for (let i = 0; i < fullDaySchedule.length; i++) {
    const block = fullDaySchedule[i];

    // Condition 1: Target time is within this block
    if (block.start <= targetTimeStr && block.end > targetTimeStr) {
      // Check if flooring the time makes sense (doesn't push start >= end)
      if (flooredTimeStr < block.end) {
        firstRelevantIndex = i;
        needsTruncation = true;
        break;
      } else {
        // Flooring pushes start >= end, treat this block as finished
        continue;
      }
    }

    // Condition 2: This block starts at or after the target time
    if (block.start >= targetTimeStr) {
      firstRelevantIndex = i;
      needsTruncation = false;
      break;
    }
  }

  // No relevant blocks found
  if (firstRelevantIndex === -1) {
    return [];
  }

  // Slice the array to get blocks from the relevant one onwards
  const relevantSchedule = fullDaySchedule.slice(firstRelevantIndex);

  // Apply truncation if needed
  if (needsTruncation && relevantSchedule.length > 0) {
    // Create a new object with the modified start time
    relevantSchedule[0] = {
      ...relevantSchedule[0],
      start: flooredTimeStr,
    };
  }

  return relevantSchedule;
}

/**
 * GET /api/room-schedule
 *
 * Query parameters:
 * - buildingId: Building code (required, e.g., "BA1")
 * - roomNumber: Room number (required, e.g., "O107")
 * - date: YYYY-MM-DD (optional, defaults to current date in ET)
 * - time: HH:mm:ss (optional, defaults to current time in ET)
 *
 * Returns: Array of RoomScheduleBlock objects
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const buildingId = searchParams.get("buildingId");
  const roomNumber = searchParams.get("roomNumber");
  let date = searchParams.get("date");
  const time = searchParams.get("time");

  // Validate required parameters
  if (!buildingId || !roomNumber) {
    return NextResponse.json(
      { error: "Missing required parameters: buildingId and roomNumber" },
      { status: 400 }
    );
  }

  // Get current time in ET
  const nowET = moment().tz(TIMEZONE);

  // Use provided date or default to current date
  if (!date) {
    date = nowET.format("YYYY-MM-DD");
  } else if (!isValidDateFormat(date)) {
    return NextResponse.json(
      { error: "Invalid date format. Use YYYY-MM-DD." },
      { status: 400 }
    );
  }

  // Determine target time
  let targetET: moment.Moment;
  if (time) {
    targetET = moment.tz(`${date}T${time}`, TIMEZONE);

    if (!targetET.isValid()) {
      console.warn("Invalid time parameter, using current time instead");
      targetET = nowET.clone();
    }
  } else {
    // Use current time but on the specified date
    targetET = moment.tz(date, "YYYY-MM-DD", TIMEZONE);
    targetET.hour(nowET.hour()).minute(nowET.minute()).second(nowET.second());
  }

  const targetTimeStr = targetET.format("HH:mm:ss");

  // Calculate floored time (round down to nearest 10 minutes)
  // This provides a cleaner start time for display
  const targetMinutes = targetET.minutes();
  const flooredMinutes = Math.floor(targetMinutes / 10) * 10;
  const flooredTargetET = targetET
    .clone()
    .minutes(flooredMinutes)
    .seconds(0)
    .milliseconds(0);
  const flooredTimeStr = flooredTargetET.format("HH:mm:ss");

  try {
    // Validate environment variables
    // Support both naming conventions
    const supabaseUrl =
      process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey =
      process.env.SUPABASE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      console.error("Missing Supabase environment variables");
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Call the cached room schedule RPC function
    const { data, error } = await supabase.rpc("get_room_schedule_cached", {
      building_id_param: buildingId,
      room_number_param: roomNumber,
      check_date_param: date,
    });

    if (error) {
      console.error(`Supabase error for ${buildingId} - ${roomNumber}:`, error);
      return NextResponse.json(
        { error: "Database error fetching schedule" },
        { status: 500 }
      );
    }

    // Parse the response
    const fullDaySchedule: RoomScheduleBlock[] = Array.isArray(data)
      ? data
      : [];

    // If no schedule data, return empty array
    if (fullDaySchedule.length === 0) {
      return NextResponse.json([]);
    }

    // Filter to only include blocks from the current time onwards
    const relevantSchedule = filterScheduleFromTime(
      fullDaySchedule,
      targetTimeStr,
      flooredTimeStr
    );

    return NextResponse.json(relevantSchedule);
  } catch (error: unknown) {
    console.error(
      `Error in /api/room-schedule for ${buildingId} - ${roomNumber}:`,
      error
    );

    const errorMessage =
      error instanceof Error ? error.message : "Failed to fetch room schedule";

    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
