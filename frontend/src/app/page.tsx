"use client";

import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Map from "@/components/Map";
import Sidebar from "@/components/Sidebar";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { FacilityStatus } from "@/types";
import { useDateTimeContext } from "@/lib/DateTimeContext";
import { getUpdatedAccordionItems } from "@/utils/accordion";

async function fetchFacilities(
  date: string,
  time: string,
): Promise<FacilityStatus> {
  const res = await fetch(`/api/facilities?date=${date}&time=${time}`);
  if (!res.ok) {
    throw new Error("Failed to fetch facilities");
  }
  return res.json();
}

export default function Home() {
  const { formattedDate, formattedTime } = useDateTimeContext();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [scrollToBuildingId, setScrollToBuildingId] = useState<string | null>(
    null,
  );

  const {
    data: facilityData,
    isLoading,
    isFetching,
    error,
  } = useQuery({
    queryKey: ["facilities", formattedDate, formattedTime],
    queryFn: () => fetchFacilities(formattedDate, formattedTime),
  });

  const handleToggleBuilding = useCallback(
    (id: string, options?: { scroll?: boolean }) => {
      setExpandedItems((prev) => getUpdatedAccordionItems(id, prev));
      if (options?.scroll) {
        setScrollToBuildingId(id);
      }
    },
    [],
  );

  const handleMarkerClick = useCallback(
    (id: string) => handleToggleBuilding(id, { scroll: true }),
    [handleToggleBuilding],
  );
  const handleBuildingClick = useCallback(
    (id: string) => handleToggleBuilding(id),
    [handleToggleBuilding],
  );

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-red-500 text-lg">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="relative h-dvh overflow-hidden">
      {/* Loading overlay — fades out once data arrives */}
      <div
        className={`absolute inset-0 z-50 flex items-center justify-center bg-zinc-950 transition-opacity duration-500 ${
          isLoading ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        <LoadingSpinner />
      </div>

      {/* Main content — fades in once data arrives */}
      <main
        className={`h-full overflow-hidden flex flex-col md:flex-row transition-opacity duration-500 ${
          isLoading ? "opacity-0" : "opacity-100"
        }`}
      >
        {/* Map - Top on mobile, Right on desktop */}
        <div className="h-[40dvh] md:h-full w-full md:w-[63%] order-1 md:order-2 shrink-0">
          <Map
            facilityData={facilityData || null}
            onMarkerClick={handleMarkerClick}
          />
        </div>

        {/* Sidebar - Bottom on mobile, Left on desktop */}
        <div className="flex-1 min-h-0 md:flex-none md:h-full w-full md:w-[37%] order-2 md:order-1 overflow-hidden border-t md:border-t-0 md:border-r border-border-subtle">
          <Sidebar
            facilityData={facilityData || null}
            expandedItems={expandedItems}
            setExpandedItems={setExpandedItems}
            onBuildingClick={handleBuildingClick}
            scrollToBuildingId={scrollToBuildingId}
            isFetching={isFetching && !isLoading}
          />
        </div>
      </main>
    </div>
  );
}
