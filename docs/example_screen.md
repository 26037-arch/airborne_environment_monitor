# Ground Station screen

The left side is grouped as required by schema v3:

```text
Environment: temperature, humidity, pressure, barometric altitude
Position:    latitude, longitude, GPS altitude, GPS ground speed/course
IMU:         ax/ay/az and gx/gy/gz
System:      schema, sequence/runtime, ENV/IMU/GPS/RTC/SD,
             RTC timestamp, packets received/lost/loss percent
```

The right side plots a selectable recent series. Every valid row is still flushed to the PC CSV even after it scrolls out of the graph. Fields unavailable in v1/v2 or failed v3 subsystems display `N/A`.
