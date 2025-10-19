/**
 * Schedule calculation utilities for light devices
 */

export interface AutoProgram {
  id: string;
  label: string;
  enabled: boolean;
  days: string[];
  sunrise: string;
  sunset: string;
  rampMinutes: number;
  levels: Record<string, number>;
  channels?: any[]; // Optional device channel definitions for ordering
}

export interface ScheduleInfo {
  type: 'current' | 'next' | 'none';
  program?: AutoProgram;
  status?: string;
  nextTime?: string;
}

export interface SequentialSchedule {
  program: AutoProgram;
  status: 'current' | 'next' | 'upcoming' | 'disabled';
  nextTime?: string;
  sortOrder: number; // For ordering: current=0, next=1, then by time
  channels?: any[]; // Optional device channel definitions for ordering
}

/**
 * Get current day of week as lowercase string (monday, tuesday, etc.)
 */
function getCurrentWeekday(): string {
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return days[new Date().getDay()];
}

/**
 * Parse time string (HH:MM) to minutes since midnight
 */
function timeToMinutes(timeStr: string): number {
  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Convert minutes since midnight back to time string
 */
function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

/**
 * Check if current time is within a program's active period
 */
function isTimeInProgram(program: AutoProgram, currentMinutes: number): boolean {
  const sunriseMinutes = timeToMinutes(program.sunrise);
  const sunsetMinutes = timeToMinutes(program.sunset);

  if (sunriseMinutes <= sunsetMinutes) {
    // Same day program (e.g., 08:00-18:00)
    return currentMinutes >= sunriseMinutes && currentMinutes <= sunsetMinutes;
  } else {
    // Overnight program (e.g., 20:00-08:00)
    return currentMinutes >= sunriseMinutes || currentMinutes <= sunsetMinutes;
  }
}

/**
 * Get next occurrence of a program (either today or another day this week)
 */
function getNextOccurrence(program: AutoProgram, currentWeekday: string, currentMinutes: number): { day: string; time: string; minutes: number } | null {
  const weekdays = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const currentDayIndex = weekdays.indexOf(currentWeekday);
  const sunriseMinutes = timeToMinutes(program.sunrise);

  // Check if program runs today and hasn't started yet
  if (program.days.includes(currentWeekday) && currentMinutes < sunriseMinutes) {
    return {
      day: 'today',
      time: program.sunrise,
      minutes: sunriseMinutes
    };
  }

  // Find next day in the week that this program runs
  for (let i = 1; i <= 7; i++) {
    const checkDayIndex = (currentDayIndex + i) % 7;
    const checkDay = weekdays[checkDayIndex];

    if (program.days.includes(checkDay)) {
      const dayName = i === 1 ? 'tomorrow' : checkDay;
      return {
        day: dayName,
        time: program.sunrise,
        minutes: sunriseMinutes + (i * 24 * 60) // Add days in minutes for sorting
      };
    }
  }

  return null;
}

/**
 * Determine current schedule status for a light device
 */
export function getCurrentScheduleInfo(programs: AutoProgram[]): ScheduleInfo {
  if (!programs || programs.length === 0) {
    return { type: 'none', status: 'No auto programs configured' };
  }

  const now = new Date();
  const currentWeekday = getCurrentWeekday();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  // Check for active programs today
  const activePrograms = programs.filter(program =>
    program.enabled &&
    program.days.includes(currentWeekday) &&
    isTimeInProgram(program, currentMinutes)
  );

  if (activePrograms.length > 0) {
    // If multiple programs are active, show the one with the latest start time
    const currentProgram = activePrograms.reduce((latest, program) => {
      const latestStart = timeToMinutes(latest.sunrise);
      const programStart = timeToMinutes(program.sunrise);
      return programStart > latestStart ? program : latest;
    });

    return {
      type: 'current',
      program: currentProgram,
      status: `Active: ${currentProgram.label} (until ${currentProgram.sunset})`
    };
  }

  // Find next upcoming program
  const enabledPrograms = programs.filter(program => program.enabled);
  if (enabledPrograms.length === 0) {
    return { type: 'none', status: 'All auto programs disabled' };
  }

  const nextOccurrences = enabledPrograms
    .map(program => {
      const occurrence = getNextOccurrence(program, currentWeekday, currentMinutes);
      return occurrence ? { program, ...occurrence } : null;
    })
    .filter(Boolean)
    .sort((a, b) => a!.minutes - b!.minutes);

  if (nextOccurrences.length > 0) {
    const next = nextOccurrences[0]!;
    return {
      type: 'next',
      program: next.program,
      status: `Next: ${next.program.label}`,
      nextTime: `${next.day} at ${next.time}`
    };
  }

  return { type: 'none', status: 'No scheduled programs found' };
}

/**
 * Get all schedules in sequential running order for display
 */
export function getAllSchedulesInOrder(programs: AutoProgram[]): SequentialSchedule[] {
  if (!programs || programs.length === 0) {
    return [];
  }

  const now = new Date();
  const currentWeekday = getCurrentWeekday();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  const schedules: SequentialSchedule[] = [];

  // First, check for currently active programs
  const activePrograms = programs.filter(program =>
    program.enabled &&
    program.days.includes(currentWeekday) &&
    isTimeInProgram(program, currentMinutes)
  );

  // Add active programs first (green)
  activePrograms.forEach(program => {
    schedules.push({
      program,
      status: 'current',
      sortOrder: 0,
      channels: program.channels
    });
  });

  // Find next upcoming program (blue)
  const enabledPrograms = programs.filter(program => program.enabled);
  if (enabledPrograms.length > 0) {
    const nextOccurrences = enabledPrograms
      .map(program => {
        const occurrence = getNextOccurrence(program, currentWeekday, currentMinutes);
        return occurrence ? { program, ...occurrence } : null;
      })
      .filter(Boolean)
      .sort((a, b) => a!.minutes - b!.minutes);

    if (nextOccurrences.length > 0) {
      const next = nextOccurrences[0]!;
      // Only add if not already in active programs
      if (!activePrograms.find(p => p.id === next.program.id)) {
        schedules.push({
          program: next.program,
          status: 'next',
          nextTime: `${next.day} at ${next.time}`,
          sortOrder: 1,
          channels: next.program.channels
        });
      }
    }
  }

  // Add all other enabled programs (grey) - upcoming ones
  enabledPrograms.forEach(program => {
    // Skip if already added as current or next
    if (!schedules.find(s => s.program.id === program.id)) {
      const occurrence = getNextOccurrence(program, currentWeekday, currentMinutes);
      if (occurrence) {
        schedules.push({
          program,
          status: 'upcoming',
          nextTime: `${occurrence.day} at ${occurrence.time}`,
          sortOrder: occurrence.minutes,
          channels: program.channels
        });
      }
    }
  });

  // Add disabled programs (red) - to be implemented soon
  const disabledPrograms = programs.filter(program => !program.enabled);
  disabledPrograms.forEach(program => {
    schedules.push({
      program,
      status: 'disabled',
      sortOrder: 999, // Put disabled at the end
      channels: program.channels
    });
  });

  // Sort by sortOrder, then by program label for consistent ordering
  return schedules.sort((a, b) => {
    if (a.sortOrder !== b.sortOrder) {
      return a.sortOrder - b.sortOrder;
    }
    return a.program.label.localeCompare(b.program.label);
  });
}
