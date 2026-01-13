"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import moment from "moment-timezone";

const TIMEZONE = "America/New_York";

interface DateTimeContextType {
  selectedDateTime: Date;
  setSelectedDateTime: (date: Date) => void;
  formattedDate: string;
  formattedTime: string;
  isCurrentDateTime: boolean;
  resetToCurrentDateTime: () => void;
  getMoment: () => moment.Moment;
}

const DateTimeContext = createContext<DateTimeContextType | undefined>(
  undefined
);

export function DateTimeProvider({ children }: { children: ReactNode }) {
  const [selectedDateTime, setSelectedDateTime] = useState<Date>(() => {
    return moment().tz(TIMEZONE).toDate();
  });

  // Format the date as YYYY-MM-DD for API calls (in UCF timezone)
  const formattedDate = moment(selectedDateTime)
    .tz(TIMEZONE)
    .format("YYYY-MM-DD");

  // Format the time as HH:mm:ss for API calls (in UCF timezone)
  const formattedTime = moment(selectedDateTime)
    .tz(TIMEZONE)
    .format("HH:mm:ss");

  // Check if the selected date/time is the current date/time
  const isCurrentDateTime = (): boolean => {
    const now = moment().tz(TIMEZONE);
    const selected = moment(selectedDateTime).tz(TIMEZONE);
    const diffMinutes = Math.abs(now.diff(selected, "minutes"));
    return diffMinutes < 1;
  };

  // Reset to current date/time
  const resetToCurrentDateTime = () => {
    setSelectedDateTime(moment().tz(TIMEZONE).toDate());
  };

  // Get moment object for advanced operations
  const getMoment = (): moment.Moment => {
    return moment(selectedDateTime).tz(TIMEZONE);
  };

  return (
    <DateTimeContext.Provider
      value={{
        selectedDateTime,
        setSelectedDateTime,
        formattedDate,
        formattedTime,
        isCurrentDateTime: isCurrentDateTime(),
        resetToCurrentDateTime,
        getMoment,
      }}
    >
      {children}
    </DateTimeContext.Provider>
  );
}

export function useDateTimeContext() {
  const context = useContext(DateTimeContext);
  if (context === undefined) {
    throw new Error(
      "useDateTimeContext must be used within a DateTimeProvider"
    );
  }
  return context;
}
