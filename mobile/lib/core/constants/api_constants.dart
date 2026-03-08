/// Backend API base URL. Emulator: 10.0.2.2:8000, fiziksel cihaz: bilgisayar IP.
const String kBaseUrl = 'http://10.0.2.2:8000';

class ApiEndpoints {
  static const String login = '/auth/login';
  static const String me = '/me';
  static const String cameras = '/cameras';
  static const String incidents = '/incidents';
}
