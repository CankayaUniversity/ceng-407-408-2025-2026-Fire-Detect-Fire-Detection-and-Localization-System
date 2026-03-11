class CameraModel {
  final int id;
  final String name;
  final String location;
  final String? rtspUrl;
  final DateTime? createdAt;

  CameraModel({
    required this.id,
    required this.name,
    required this.location,
    this.rtspUrl,
    this.createdAt,
  });

  factory CameraModel.fromJson(Map<String, dynamic> json) {
    return CameraModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      location: json['location'] as String? ?? '',
      rtspUrl: json['rtsp_url'] as String?,
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'] as String) : null,
    );
  }
}
