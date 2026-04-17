import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/shared/models/user_model.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class AuthService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _token;
  String? _refreshToken;
  UserModel? _user;

  String? get token => _token;
  UserModel? get user => _user;
  bool get isLoggedIn => _token != null && _token!.isNotEmpty;

  Future<void> loadToken() async {
    _token = await _storage.read(key: StorageKeys.accessToken);
    _refreshToken = await _storage.read(key: StorageKeys.refreshToken);
    if (_token != null) await _fetchMe();
    notifyListeners();
  }

  Future<void> _fetchMe() async {
    try {
      final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
      dio.options.headers['Authorization'] = 'Bearer $_token';
      final r = await dio.get(ApiEndpoints.me);
      _user = UserModel.fromJson(r.data as Map<String, dynamic>);
    } catch (_) {
      _user = null;
    }
    notifyListeners();
  }

  Future<String?> getToken() async {
    _token ??= await _storage.read(key: StorageKeys.accessToken);
    return _token;
  }

  Future<bool> login(String email, String password) async {
    try {
      final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
      final r = await dio.post(
        ApiEndpoints.login,
        data: {'email': email, 'password': password},
      );
      final accessToken = r.data['access_token'] as String?;
      final refreshToken = r.data['refresh_token'] as String?;
      
      if (accessToken == null || accessToken.isEmpty) return false;
      
      _token = accessToken;
      await _storage.write(key: StorageKeys.accessToken, value: accessToken);
      
      if (refreshToken != null && refreshToken.isNotEmpty) {
        _refreshToken = refreshToken;
        await _storage.write(key: StorageKeys.refreshToken, value: refreshToken);
      }
      
      await _fetchMe();
      await _syncFCMToken();
      notifyListeners();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> _syncFCMToken() async {
    try {
      final fcmToken = await FirebaseMessaging.instance.getToken();
      if (fcmToken != null) {
        final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
        dio.options.headers['Authorization'] = 'Bearer $_token';
        await dio.post('/me/fcm-token', data: {'fcm_token': fcmToken});
      }
    } catch (_) {}
  }

  Future<bool> refreshAccessToken() async {
    try {
      _refreshToken ??= await _storage.read(key: StorageKeys.refreshToken);
      if (_refreshToken == null || _refreshToken!.isEmpty) return false;
      
      final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
      final r = await dio.post(
        ApiEndpoints.refresh,
        data: {'refresh_token': _refreshToken},
      );
      
      final newAccessToken = r.data['access_token'] as String?;
      // If the backend returns a new refresh token, we can update it too
      final newRefreshToken = r.data['refresh_token'] as String?;
      
      if (newAccessToken != null && newAccessToken.isNotEmpty) {
        _token = newAccessToken;
        await _storage.write(key: StorageKeys.accessToken, value: newAccessToken);
        
        if (newRefreshToken != null && newRefreshToken.isNotEmpty) {
           _refreshToken = newRefreshToken;
           await _storage.write(key: StorageKeys.refreshToken, value: newRefreshToken);
        }
        
        notifyListeners();
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    if (_refreshToken != null) {
      try {
        final dio = Dio(BaseOptions(baseUrl: kBaseUrl));
        await dio.post(
          ApiEndpoints.logout,
          data: {'refresh_token': _refreshToken},
        );
      } catch (_) {
        // Ignore network errors on logout
      }
    }
    
    _token = null;
    _refreshToken = null;
    _user = null;
    await _storage.delete(key: StorageKeys.accessToken);
    await _storage.delete(key: StorageKeys.refreshToken);
    notifyListeners();
  }
}
