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
    );
  }

  bool get canStream => rtspUrl != null && rtspUrl!.isNotEmpty;
  bool get isDetected => status == 'DETECTED';
  bool get isConfirmed => status == 'CONFIRMED';
}
