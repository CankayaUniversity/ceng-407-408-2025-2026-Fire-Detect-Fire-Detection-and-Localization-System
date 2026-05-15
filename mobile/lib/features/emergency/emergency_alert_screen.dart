import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/theme/app_theme.dart';
import 'package:flamescope/shared/models/incident_model.dart';

class EmergencyAlertScreen extends StatefulWidget {
  const EmergencyAlertScreen({super.key});

  @override
  State<EmergencyAlertScreen> createState() => _EmergencyAlertScreenState();
}

class _EmergencyAlertScreenState extends State<EmergencyAlertScreen> {
  List<IncidentModel> _confirmed = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    final dio = createDio(auth);
    try {
      final r = await dio.get(ApiEndpoints.incidents);
      final list = (r.data['incidents'] as List?)?.map((e) => IncidentModel.fromJson(e as Map<String, dynamic>)).toList() ?? [];
      if (mounted) setState(() {
        _confirmed = list.where((e) => e.isConfirmed).toList();
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e is DioException ? (e.response?.statusMessage ?? 'Bağlantı hatası') : 'Yüklenemedi';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Acil Durum Bildirimleri'),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.pop()),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      FilledButton(onPressed: _load, child: const Text('Tekrar Dene')),
                    ],
                  ),
                )
              : _confirmed.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.check_circle_outline, size: 64, color: AppColors.safe),
                          SizedBox(height: 16),
                          Text('Aktif acil durum yok'),
                        ],
                      ),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: const Color(0xFF4A3310),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: AppColors.warning.withValues(alpha: 0.35),
                            ),
                          ),
                          child: Text(
                              'Kaçış: En yakın acil çıkışı kullanın. Asansör kullanmayın.',
                              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                    color: const Color(0xFFFFE7B0),
                                    fontWeight: FontWeight.w800,
                                  ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        ..._confirmed.map(
                          (inc) => Card(
                            color: const Color(0xFF3A1412),
                            child: ListTile(
                              leading: Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: AppColors.danger.withValues(alpha: 0.18),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: const Icon(
                                  Icons.warning_amber,
                                  color: Color(0xFFFFB4AB),
                                ),
                              ),
                              title: Text(
                                inc.cameraName ?? 'Kamera #${inc.cameraId}',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              subtitle: Text(
                                '${inc.cameraLocation ?? '-'} • Doğrulanmış yangın',
                                style: const TextStyle(
                                  color: Color(0xFFFFDAD6),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
    );
  }
}
