import 'package:dio/dio.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/data/models/notification_model.dart';

class NotificationsApi {
  final Dio _dio;

  NotificationsApi(this._dio);

  Future<List<NotificationModel>> getMyNotifications() async {
    final response = await _dio.get(ApiEndpoints.notifications);
    final data = response.data as List;
    return data.map((e) => NotificationModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<NotificationModel> markAsRead(int notificationId) async {
    final response = await _dio.post(ApiEndpoints.markNotificationRead(notificationId));
    return NotificationModel.fromJson(response.data as Map<String, dynamic>);
  }
}
