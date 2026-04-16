import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/shared/models/user_model.dart';

class AuthService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _token;
  UserModel? _user;

  String? get token => _token;
  UserModel? get user => _user;
  bool get isLoggedIn => _token != null && _token!.isNotEmpty;

  Future<void> loadToken() async {
    _token = await _storage.read(key: StorageKeys.accessToken);
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
      if (accessToken == null || accessToken.isEmpty) return false;
      _token = accessToken;
      await _storage.write(key: StorageKeys.accessToken, value: accessToken);
      await _fetchMe();
      notifyListeners();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    _user = null;
    await _storage.delete(key: StorageKeys.accessToken);
    notifyListeners();
  }
}
