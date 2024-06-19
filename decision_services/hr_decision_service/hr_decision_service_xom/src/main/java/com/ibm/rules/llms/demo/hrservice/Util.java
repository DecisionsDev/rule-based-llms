package com.ibm.rules.llms.demo.hrservice;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;

public class Util {

    public static ZonedDateTime parseDate(String dateAsString)
    {
        // try several format to get a date from the given string
        LocalDate localDate = null;
        boolean failed = false;
        try {
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("MMMM d, yyyy");
            localDate = LocalDate.parse(dateAsString, formatter);
        } catch(DateTimeParseException ex) {
            failed = true;
        }
        if (failed) {
            try {
                DateTimeFormatter formatter = DateTimeFormatter.ofPattern("MMM d, yyyy");
                localDate = LocalDate.parse(dateAsString, formatter);
                failed = false;
            } catch(DateTimeParseException ex) {
                failed = true;
            }

        }
        if (failed) {
            try {
                DateTimeFormatter formatter = DateTimeFormatter.ISO_LOCAL_DATE;
                localDate = LocalDate.parse(dateAsString, formatter);
                failed = false;
            } catch(DateTimeParseException ex) {
                failed = true;
            }
        }
        if (failed) {
            try {
                DateTimeFormatter formatter = DateTimeFormatter.ISO_DATE;
                localDate = LocalDate.parse(dateAsString, formatter);
                failed = false;
            } catch(DateTimeParseException ex) {
                failed = true;
            }
        }
        if (failed) {
            try {
                DateTimeFormatter formatter = DateTimeFormatter.RFC_1123_DATE_TIME;
                localDate = LocalDate.parse(dateAsString, formatter);
                failed = false;
            } catch(DateTimeParseException ex) {
                failed = true;
            }
        }
        if (!failed) {
            return ZonedDateTime.of(localDate, LocalTime.MIDNIGHT, java.time.ZoneId.systemDefault());
        } else {
            return null;
        }
    }

    public static boolean isBefore(String aDate, String anotherDate)
    {
        ZonedDateTime date1 = parseDate(aDate);
        ZonedDateTime date2 = parseDate(anotherDate);

        if (date1 == null) {
            throw new RuntimeException("Malformed date: " + aDate);
        }
        if (date2 == null) {
            throw new RuntimeException("Malformed date: " + anotherDate);
        }
        return date1.isBefore(date2);
    }

    public static boolean isAfter(String aDate, String anotherDate)
    {
        ZonedDateTime date1 = parseDate(aDate);
        ZonedDateTime date2 = parseDate(anotherDate);

        if (date1 == null) {
            throw new RuntimeException("Malformed date: " + aDate);
        }
        if (date2 == null) {
            throw new RuntimeException("Malformed date: " + anotherDate);
        }
        return date1.isAfter(date2);
    }

    public static boolean isSameDate(String aDate, String anotherDate)
    {
        ZonedDateTime date1 = parseDate(aDate);
        ZonedDateTime date2 = parseDate(anotherDate);

        if (date1 == null) {
            throw new RuntimeException("Malformed date: " + aDate);
        }
        if (date2 == null) {
            throw new RuntimeException("Malformed date: " + anotherDate);
        }
        return date1.isEqual(date2);
    }

    public static long yearsOfService(String hiringDate)
    {
        ZonedDateTime date = parseDate(hiringDate);
        if (date == null) {
            throw new RuntimeException("Malformed date: " + hiringDate);
        }
        return ChronoUnit.YEARS.between(date, ZonedDateTime.now());
    }



}
