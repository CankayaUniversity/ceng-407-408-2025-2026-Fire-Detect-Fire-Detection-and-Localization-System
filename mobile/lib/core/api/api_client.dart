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
      // Handle 401 Unauthorized
      if (err.response?.statusCode == 401) {
        // Prevent infinite loop if the refresh endpoint itself throws 401
        if (err.requestOptions.path == ApiEndpoints.refresh) {
          await authService.logout();
          return handler.next(err);
        }

        // Try to refresh the token
        final success = await authService.refreshAccessToken();
        if (success) {
          try {
            // Retrieve the newly acquired token
            final newToken = await authService.getToken();
            final options = err.requestOptions;
            options.headers['Authorization'] = 'Bearer $newToken';

            // Retry the original request
            final retryDio = Dio(dio.options);
            final response = await retryDio.fetch(options);
            return handler.resolve(response);
          } catch (retryError) {
            return handler.next(retryError as DioException);
          }
        } else {
          // Token refresh failed, must re-login
          await authService.logout();
          return handler.next(err);
        }
      }
      return handler.next(err);
    },
  ));

  return dio;
}
