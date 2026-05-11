"use client";

import { useState, useEffect, useMemo } from "react";
import { RotateCcw, ChevronLeft, ChevronRight, Clock } from "lucide-react";
import { Input } from "@/components/ui/input";
import moment from "moment-timezone";

interface DateTimePickerProps {
  initialDateTime?: Date;
  onDateTimeChange?: (dateTime: Date) => void;
  closeContainer?: () => void;
  minDate?: Date;
  maxDate?: Date;
}

const TIMEZONE = "America/New_York";

export function DateTimePicker({
  initialDateTime = new Date(),
  onDateTimeChange,
  closeContainer,
  minDate,
  maxDate,
}: DateTimePickerProps) {
  const initialMoment = useMemo(
    () => moment(initialDateTime).tz(TIMEZONE),
    [initialDateTime],
  );

  const [selectedDate, setSelectedDate] = useState<Date>(() =>
    initialMoment.toDate(),
  );
  const [currentMonth, setCurrentMonth] = useState(() => initialMoment.clone());
  const [timeValue, setTimeValue] = useState(() =>
    initialMoment.format("HH:mm"),
  );

  useEffect(() => {
    setSelectedDate(initialMoment.toDate());
    setCurrentMonth(initialMoment.clone());
    setTimeValue(initialMoment.format("HH:mm"));
  }, [initialMoment]);

  const getCombinedDateTime = (date: Date, time: string): Date => {
    const [hours, minutes] = time.split(":").map(Number);
    const combined = moment(date).tz(TIMEZONE);
    combined.hour(hours);
    combined.minute(minutes);
    combined.second(0);
    return combined.toDate();
  };

  const handleDateSelect = (day: number) => {
    const newDate = currentMonth.clone().date(day);
    setSelectedDate(newDate.toDate());
  };

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTimeValue(e.target.value);
  };

  const commit = (dateTime: Date) => {
    onDateTimeChange?.(dateTime);
    closeContainer?.();
  };

  const handleConfirm = () => {
    commit(getCombinedDateTime(selectedDate, timeValue));
  };

  const handleReset = () => {
    const now = moment().tz(TIMEZONE);
    setSelectedDate(now.toDate());
    setCurrentMonth(now);
    setTimeValue(now.format("HH:mm"));
    commit(now.toDate());
  };

  const minDateMoment = minDate
    ? moment(minDate).tz(TIMEZONE)
    : moment().tz(TIMEZONE).startOf("day");
  const maxDateMoment = maxDate
    ? moment(maxDate).tz(TIMEZONE).endOf("day")
    : null;

  const previousMonth = () => {
    if (canGoPrevious()) {
      setCurrentMonth(currentMonth.clone().subtract(1, "month"));
    }
  };

  const nextMonth = () => {
    if (canGoNext()) {
      setCurrentMonth(currentMonth.clone().add(1, "month"));
    }
  };

  const canGoPrevious = () => {
    const prevMonth = currentMonth.clone().subtract(1, "month");
    return prevMonth.isSameOrAfter(minDateMoment, "month");
  };

  const canGoNext = () => {
    if (!maxDateMoment) return true;
    const nextMonth = currentMonth.clone().add(1, "month");
    return nextMonth.isSameOrBefore(maxDateMoment, "month");
  };

  // Get calendar days
  const startOfMonth = currentMonth.clone().startOf("month");
  const endOfMonth = currentMonth.clone().endOf("month");
  const startOfCalendar = startOfMonth.clone().startOf("week");
  const endOfCalendar = endOfMonth.clone().endOf("week");

  const calendarDays: Array<{ day: number; isCurrentMonth: boolean }> = [];
  const current = startOfCalendar.clone();
  while (current.isSameOrBefore(endOfCalendar, "day")) {
    calendarDays.push({
      day: current.date(),
      isCurrentMonth: current.isSame(currentMonth, "month"),
    });
    current.add(1, "day");
  }

  const today = moment().tz(TIMEZONE);
  const isToday = (day: number) => {
    return currentMonth.clone().date(day).isSame(today, "day");
  };

  const isSelected = (day: number) => {
    return currentMonth
      .clone()
      .date(day)
      .isSame(moment(selectedDate).tz(TIMEZONE), "day");
  };

  const isDisabled = (day: number) => {
    const dateMoment = currentMonth.clone().date(day);
    if (dateMoment.isBefore(minDateMoment, "day")) {
      return true;
    }
    if (maxDateMoment && dateMoment.isAfter(maxDateMoment, "day")) {
      return true;
    }
    return false;
  };

  const currentDateTime = getCombinedDateTime(selectedDate, timeValue);
  const previewText = moment(currentDateTime)
    .tz(TIMEZONE)
    .format("M/D/YY h:mm A");

  return (
    <div className="w-[min(280px,calc(100vw-1rem))] bg-surface-raised rounded-lg border border-border-muted">
      {/* Calendar Section */}
      <div className="p-2 sm:p-3">
        {/* Month Header */}
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={previousMonth}
            disabled={!canGoPrevious()}
            className="p-1 hover:bg-zinc-800 rounded transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4 text-zinc-300" />
          </button>
          <h3 className="text-sm font-medium text-foreground">
            {currentMonth.format("MMMM YYYY")}
          </h3>
          <button
            onClick={nextMonth}
            disabled={!canGoNext()}
            className="p-1 hover:bg-zinc-800 rounded transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Next month"
          >
            <ChevronRight className="h-4 w-4 text-zinc-300" />
          </button>
        </div>

        {/* Day Names */}
        <div className="grid grid-cols-7 gap-1 mb-1">
          {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
            <div
              key={day}
              className="text-xs font-medium text-zinc-400 text-center py-1"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1">
          {calendarDays.map(({ day, isCurrentMonth }, index) => {
            if (!isCurrentMonth) {
              return (
                <div
                  key={index}
                  className="h-8 flex items-center justify-center text-zinc-600 text-sm"
                >
                  {day}
                </div>
              );
            }

            const dayIsToday = isToday(day);
            const dayIsSelected = isSelected(day);
            const dayIsDisabled = isDisabled(day);

            return (
              <button
                key={index}
                onClick={() => !dayIsDisabled && handleDateSelect(day)}
                disabled={dayIsDisabled}
                className={`h-8 rounded-md text-sm transition-colors relative ${
                  dayIsDisabled
                    ? "text-zinc-600 cursor-not-allowed opacity-50"
                    : dayIsSelected
                      ? "cursor-pointer bg-yellow-500/20 text-yellow-400 border border-yellow-500/40"
                      : dayIsToday
                        ? "cursor-pointer bg-zinc-800 text-zinc-200"
                        : "cursor-pointer text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {day}
              </button>
            );
          })}
        </div>
      </div>

      {/* Time Input Section */}
      <div className="border-t border-border-muted p-2 sm:p-3">
        <div className="flex items-center gap-3">
          <label className="text-xs text-zinc-300 whitespace-nowrap">
            Enter time
          </label>
          <div className="flex-1 relative">
            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-secondary pointer-events-none z-10" />
            <Input
              type="time"
              value={timeValue}
              onChange={handleTimeChange}
              className="bg-surface-raised border-border-muted text-zinc-200 focus-visible:ring-zinc-600 pl-9 text-base sm:text-sm text-right cursor-pointer [&::-webkit-calendar-picker-indicator]:hidden [&::-webkit-calendar-picker-indicator]:appearance-none"
            />
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="border-t border-border-muted p-2 sm:p-3 flex items-center justify-between">
        <p className="text-xs text-zinc-400">{previewText}</p>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="h-7 px-2 flex items-center gap-1 rounded-md bg-surface-raised border border-border-muted text-zinc-300 hover:bg-surface-hover text-xs font-medium transition-colors cursor-pointer"
          >
            <RotateCcw className="h-3 w-3" />
            Now
          </button>
          <button
            onClick={handleConfirm}
            className="h-7 px-3 rounded-md bg-surface-raised text-zinc-200 hover:bg-surface-hover border border-border-muted text-xs font-medium transition-colors cursor-pointer"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
