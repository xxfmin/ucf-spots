// ============================================
// UCF Spots Type Definitions
// ============================================

/**
 * Facility type (keeping as enum for potential future expansion)
 */
export enum FacilityType {
  ACADEMIC = "academic",
}

/**
 * Room availability status
 */
export enum RoomStatus {
  AVAILABLE = "available",
  OCCUPIED = "occupied",
  PASSING_PERIOD = "passing_period",
  OPENING_SOON = "opening_soon",
}

// ============================================
// API Response Types
// ============================================

/**
 * Main API response from /api/facilities
 */
export interface FacilityStatus {
  timestamp: string;
  facilities: Record<string, Facility>;
}

/**
 * Building/Facility data
 */
export interface Facility {
  id: string;
  name: string;
  type: FacilityType;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  hours: {
    open: string;
    close: string;
  };
  rooms: Record<string, AcademicRoom>;
  isOpen: boolean;
  roomCounts: {
    available: number;
    total: number;
  };
}

/**
 * Academic room data
 */
export interface AcademicRoom {
  status: RoomStatus;
  currentClass?: ClassInfo;
  nextClass?: ClassInfo;
  passingPeriod?: boolean;
  availableAt?: string; // HH:mm:ss format
  availableFor?: number; // Duration in minutes
  availableUntil?: string; // HH:mm:ss format
}

/**
 * Class/Event information
 */
export interface ClassInfo {
  type: "class" | "event";
  course: string; // Course code (e.g., "COP 3502") or event occupant
  title: string; // Course title or event name
  time?: {
    start: string; // HH:mm:ss
    end: string; // HH:mm:ss
  };
}

// ============================================
// Room Schedule Types
// ============================================

/**
 * Details for a class or event block
 */
export interface AcademicBlockDetails {
  type: "class" | "event";
  course?: string; // For classes: course code
  identifier?: string; // For events: occupant
  title: string;
}

/**
 * A single schedule block (from get_room_schedule API)
 */
export interface RoomScheduleBlock {
  start: string; // HH:mm:ss
  end: string; // HH:mm:ss
  status: "available" | "class" | "event";
  details: AcademicBlockDetails | null; // Null for 'available' status
}

/**
 * A section within an hourly block (for UI rendering)
 */
export interface BlockSection {
  start: string; // HH:mm:ss
  end: string; // HH:mm:ss
  status: "available" | "class" | "event";
  details: AcademicBlockDetails | null;
}

/**
 * An hourly block containing multiple sections (for UI rendering)
 */
export interface HourlyScheduleBlock {
  start: string; // HH:mm:ss
  end: string; // HH:mm:ss
  sections: BlockSection[];
}

// ============================================
// Component Props Types
// ============================================

/**
 * Props for the Map component
 */
export interface MapProps {
  facilityData: FacilityStatus | null;
  onMarkerClick: (id: string) => void;
  onMapLoaded?: () => void;
}

/**
 * Marker data for map rendering
 */
export interface MarkerData {
  id: string;
  name: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  isOpen: boolean;
  available: number;
  total: number;
  hours: {
    open: string;
    close: string;
  };
}

/**
 * Props for the FacilityRoomDetails component
 */
export interface FacilityRoomProps {
  roomName: string;
  room: AcademicRoom;
  buildingId: string;
}

/**
 * Props for the RoomBadge component
 */
export interface RoomBadgeProps {
  status: RoomStatus;
  availableAt?: string;
  availableFor?: number;
}

/**
 * Props for schedule display components
 */
export interface RoomScheduleProps {
  blocks: RoomScheduleBlock[];
}

/**
 * Accordion refs for scrolling to buildings
 */
export interface AccordionRefs {
  [key: string]: HTMLDivElement | null;
}

// ============================================
// Supabase RPC Response Types
// ============================================

/**
 * Response from get_spots() or get_cached_spots() RPC
 * This is the raw format from Supabase before transformation
 */
export interface GetSpotsResponse {
  timestamp: string;
  buildings: Record<
    string,
    {
      name: string;
      coordinates: {
        latitude: number;
        longitude: number;
      };
      hours: {
        open: string;
        close: string;
      };
      rooms: Record<
        string,
        {
          status: "available" | "occupied";
          available: boolean;
          currentClass: ClassInfo | null;
          nextClass: ClassInfo | null;
          passingPeriod: boolean;
          availableAt: string | null;
          availableFor: number | null;
          availableUntil: string | null;
        }
      >;
      isOpen: boolean;
      roomCounts: {
        available: number;
        total: number;
      };
    }
  >;
}
