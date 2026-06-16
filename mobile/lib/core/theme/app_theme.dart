import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light {
    const flame = Color(0xFFE65100);
    const ember = Color(0xFFC62828);
    const surface = Color(0xFFFFF7F1);
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: surface,
      colorScheme: ColorScheme.fromSeed(
        seedColor: flame,
        brightness: Brightness.light,
        primary: flame,
        error: ember,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        color: Colors.white,
        surfaceTintColor: Colors.transparent,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFFD84315),
          foregroundColor: Colors.white,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: const Color(0xFF8A4B12),
          side: const BorderSide(color: Color(0xFF8A4B12)),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
