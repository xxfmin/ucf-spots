"use client";

import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Map from "@/components/Map";
import Sidebar from "@/components/Sidebar";
import { FacilityStatus } from "@/types";
import { useDateTimeContext } from "@/lib/DateTimeContext";
import { getUpdatedAccordionItems } from "@/utils/accordion";

async function fetchFacilities(
  date: string,
  time: string
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
    null
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

  const handleMarkerClick = useCallback((id: string) => {
    setExpandedItems((prev) => getUpdatedAccordionItems(id, prev));
    setScrollToBuildingId(id);
  }, []);

  const handleBuildingClick = useCallback((id: string) => {
    // When clicking in sidebar, just toggle accordion, don't scroll
    setExpandedItems((prev) => getUpdatedAccordionItems(id, prev));
  }, []);

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 border-4 border-zinc-700 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-yellow-400 border-t-transparent rounded-full animate-spin"></div>
          </div>
          <p className="text-sm text-zinc-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-red-500 text-lg">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <main className="h-screen flex flex-col md:flex-row">
      {/* Map - Top on mobile, Right on desktop */}
      <div className="h-[40vh] md:h-screen w-full md:w-[63%] order-1 md:order-2">
        <Map
          facilityData={facilityData || null}
          onMarkerClick={handleMarkerClick}
        />
      </div>

      {/* Sidebar - Bottom on mobile, Left on desktop */}
      <div className="h-[60vh] md:h-screen w-full md:w-[37%] order-2 md:order-1 overflow-hidden border-t md:border-t-0 md:border-r border-gray-800">
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
  );
}
