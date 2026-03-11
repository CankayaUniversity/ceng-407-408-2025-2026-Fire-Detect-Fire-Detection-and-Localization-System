import 'package:dio/dio.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/auth/auth_service.dart';

Dio createDio(AuthService authService) {
  final dio = Dio(BaseOptions(
    baseUrl: kBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final token = await authService.getToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      return handler.next(options);
    },
    onError: (err, handler) async {
      if (err.response?.statusCode == 401) {
        await authService.logout();
        // Router ile login'e yönlendirme context gerektirir; bu katmanda yapılmaz.
      }
      return handler.next(err);
    },
  ));

  return dio;
}
