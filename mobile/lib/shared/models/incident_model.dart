import 'package:flamescope/core/constants/api_constants.dart';

DateTime? _parseBackendDateTime(dynamic raw) {
  if (raw is! String || raw.trim().isEmpty) return null;
  final value = raw.trim();
  final hasTimeZone =
      value.endsWith('Z') || RegExp(r'[+-]\d{2}:?\d{2}$').hasMatch(value);
  final parsed = DateTime.tryParse(hasTimeZone ? value : '${value}Z');
  return parsed?.toLocal();
}

class IncidentModel {
  final int id;
  final int cameraId;
  final String? cameraName;
  final String? cameraLocation;
  final String? rtspUrl;
  final String status;
  final double? confidence;
  final String? snapshotUrl;
  final DateTime? detectedAt;
  final DateTime? confirmedAt;
  final int? confirmedBy;
  final List<IncidentSafetyReportModel> safetyReports;
  final List<IncidentResponseUpdateModel> responseUpdates;

  IncidentModel({
    required this.id,
    required this.cameraId,
    this.cameraName,
    this.cameraLocation,
    this.rtspUrl,
    required this.status,
    this.confidence,
    this.snapshotUrl,
    this.detectedAt,
    this.confirmedAt,
    this.confirmedBy,
    this.safetyReports = const [],
    this.responseUpdates = const [],
  });

  factory IncidentModel.fromJson(Map<String, dynamic> json) {
    return IncidentModel(
      id: json['id'] as int,
      cameraId: json['camera_id'] as int,
      cameraName: json['camera_name'] as String?,
      cameraLocation: json['camera_location'] as String?,
      rtspUrl: json['rtsp_url'] as String?,
      status: json['status'] as String? ?? 'DETECTED',
      confidence: (json['confidence'] as num?)?.toDouble(),
      snapshotUrl: normalizeBackendAssetUrl(json['snapshot_url'] as String?),
      detectedAt: _parseBackendDateTime(json['detected_at']),
      confirmedAt: _parseBackendDateTime(json['confirmed_at']),
      confirmedBy: json['confirmed_by'] as int?,
      safetyReports: (json['safety_reports'] as List? ?? const [])
          .map((e) =>
              IncidentSafetyReportModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      responseUpdates: (json['response_updates'] as List? ?? const [])
          .map((e) =>
              IncidentResponseUpdateModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  bool get canStream => rtspUrl != null && rtspUrl!.isNotEmpty;
  bool get isDetected => status == 'DETECTED';
  bool get isConfirmed => status == 'CONFIRMED';
  bool get isDismissed => status == 'DISMISSED';

  String get riskLevel {
    final score = confidence;
    if (score == null) return 'UNKNOWN';
    if (score >= 0.97) return 'CRITICAL';
    if (score >= 0.80) return 'HIGH';
    if (score >= 0.60) return 'MEDIUM';
    return 'LOW';
  }

  String get riskLevelLabel {
    switch (riskLevel) {
      case 'CRITICAL':
        return 'Critical Risk';
      case 'HIGH':
        return 'High Risk';
      case 'MEDIUM':
        return 'Medium Risk';
      case 'LOW':
        return 'Low Risk';
      default:
        return 'Risk Unknown';
    }
  }
}

class IncidentSafetyReportModel {
  final int userId;
  final String userName;
  final String status;
  final DateTime? createdAt;

  IncidentSafetyReportModel({
    required this.userId,
    required this.userName,
    required this.status,
    this.createdAt,
  });

  factory IncidentSafetyReportModel.fromJson(Map<String, dynamic> json) {
    return IncidentSafetyReportModel(
      userId: json['user_id'] as int,
      userName: json['user_name'] as String? ?? 'Employee #${json['user_id']}',
      status: json['status'] as String? ?? 'SAFE',
      createdAt: _parseBackendDateTime(json['created_at']),
    );
  }

  bool get needsHelp => status == 'NEED_HELP';
  String get label => needsHelp ? 'Needs Help' : 'Safe';
}

class IncidentResponseUpdateModel {
  final int userId;
  final String userName;
  final String status;
  final DateTime? createdAt;

  IncidentResponseUpdateModel({
    required this.userId,
    required this.userName,
    required this.status,
    this.createdAt,
  });

  factory IncidentResponseUpdateModel.fromJson(Map<String, dynamic> json) {
    return IncidentResponseUpdateModel(
      userId: json['user_id'] as int,
      userName: json['user_name'] as String? ?? 'Responder #${json['user_id']}',
      status: json['status'] as String? ?? 'DISPATCHED',
      createdAt: _parseBackendDateTime(json['created_at']),
    );
  }

  String get label {
    switch (status) {
      case 'ARRIVED':
        return 'Arrived on scene';
      case 'UNDER_CONTROL':
        return 'Under control';
      case 'DISPATCHED':
      default:
        return 'Dispatched';
    }
  }
}
