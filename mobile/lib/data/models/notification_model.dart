class NotificationModel {
  final int id;
  final int userId;
  final int? incidentId;
  final String message;
  final bool isRead;
  final String createdAt;

  NotificationModel({
    required this.id,
    required this.userId,
    this.incidentId,
    required this.message,
    required this.isRead,
    required this.createdAt,
  });

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    return NotificationModel(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      incidentId: json['incident_id'] as int?,
      message: json['message'] as String,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: json['created_at'] as String,
    );
  }
}
