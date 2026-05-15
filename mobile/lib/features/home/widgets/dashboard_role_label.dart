import 'package:flamescope/core/constants/app_constants.dart';

String dashboardRoleLabel(AppRole role) {
  switch (role) {
    case AppRole.admin:
      return 'Admin';
    case AppRole.manager:
      return 'Yönetici';
    case AppRole.fireResponseUnit:
      return 'Yangın Müdahale';
    case AppRole.employee:
      return 'Çalışan';
  }
}
