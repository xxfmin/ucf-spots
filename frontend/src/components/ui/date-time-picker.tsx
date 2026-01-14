"use client";

import { useState, useEffect } from "react";
import { Clock, RotateCcw, ChevronLeft, ChevronRight } from "lucide-react";
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
  const [selectedDate, setSelectedDate] = useState<Date>(
    moment(initialDateTime).tz(TIMEZONE).toDate()
  );
  const [currentMonth, setCurrentMonth] = useState(
    moment(initialDateTime).tz(TIMEZONE)
  );
  const [timeValue, setTimeValue] = useState(
    moment(initialDateTime).tz(TIMEZONE).format("HH:mm")
  );

  useEffect(() => {
    const initial = moment(initialDateTime).tz(TIMEZONE);
    setSelectedDate(initial.toDate());
    setCurrentMonth(initial);
    setTimeValue(initial.format("HH:mm"));
  }, [initialDateTime]);

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

  const handleConfirm = () => {
    const dateTime = getCombinedDateTime(selectedDate, timeValue);
    if (onDateTimeChange) {
      onDateTimeChange(dateTime);
    }
    if (closeContainer) {
      closeContainer();
    }
  };

  const handleReset = () => {
    const now = moment().tz(TIMEZONE);
    setSelectedDate(now.toDate());
    setCurrentMonth(now);
    setTimeValue(now.format("HH:mm"));
    if (onDateTimeChange) {
      onDateTimeChange(now.toDate());
    }
    if (closeContainer) {
      closeContainer();
    }
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
    if (!minDateMoment) return true;
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
    <div className="w-[280px] bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
      {/* Calendar Section */}
      <div className="p-3">
        {/* Month Header */}
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={previousMonth}
            disabled={!canGoPrevious()}
            className="p-1 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4 text-zinc-300" />
          </button>
          <h3 className="text-sm font-medium text-zinc-100">
            {currentMonth.format("MMMM YYYY")}
          </h3>
          <button
            onClick={nextMonth}
            disabled={!canGoNext()}
            className="p-1 hover:bg-zinc-800 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  className="h-9 flex items-center justify-center text-zinc-600 text-sm"
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
                className={`h-9 rounded-md text-sm transition-colors relative ${
                  dayIsDisabled
                    ? "text-zinc-600 cursor-not-allowed opacity-50"
                    : dayIsSelected
                    ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/40"
                    : dayIsToday
                    ? "bg-zinc-800 text-zinc-200"
                    : "text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {day}
                {dayIsSelected && (
                  <span className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-zinc-900 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Time Input Section */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex items-center gap-3">
          <label className="text-xs text-zinc-300 whitespace-nowrap">
            Enter time
          </label>
          <div className="relative flex-1">
            <Clock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              type="time"
              value={timeValue}
              onChange={handleTimeChange}
              className="pl-9 bg-zinc-800 border-zinc-700 text-zinc-200 focus-visible:ring-zinc-600"
            />
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="border-t border-zinc-800 p-3 flex items-center justify-between">
        <p className="text-xs text-zinc-400">{previewText}</p>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="h-7 px-2 flex items-center gap-1 rounded-md bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 text-xs font-medium transition-colors"
          >
            <RotateCcw className="h-3 w-3" />
            Now
          </button>
          <button
            onClick={handleConfirm}
            className="h-7 px-3 rounded-md bg-zinc-800 text-zinc-200 hover:bg-zinc-700 border border-zinc-700 text-xs font-medium transition-colors"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
