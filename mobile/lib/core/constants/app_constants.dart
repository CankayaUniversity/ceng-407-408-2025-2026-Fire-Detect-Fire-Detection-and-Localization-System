class StorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
}

enum AppRole {
  admin('ADMIN'),
  manager('MANAGER'),
  employee('EMPLOYEE'),
  fireResponseUnit('FIRE_RESPONSE_UNIT');

  const AppRole(this.value);
  final String value;

  static AppRole fromString(String? v) {
    if (v == null) return AppRole.employee;
    return AppRole.values.firstWhere(
      (e) => e.value == v,
      orElse: () => AppRole.employee,
    );
  }
}
