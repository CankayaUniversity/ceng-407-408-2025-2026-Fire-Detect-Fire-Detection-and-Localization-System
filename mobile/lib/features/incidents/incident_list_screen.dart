import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/shared/models/incident_model.dart';

class IncidentListScreen extends StatefulWidget {
  const IncidentListScreen({super.key});

  @override
  State<IncidentListScreen> createState() => _IncidentListScreenState();
}

class _IncidentListScreenState extends State<IncidentListScreen> {
  List<IncidentModel> _incidents = [];
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
        _incidents = list;
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
        title: const Text('Olaylar'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
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
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _incidents.isEmpty
                      ? const Center(child: Text('Olay bulunamadı'))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _incidents.length,
                          itemBuilder: (context, i) {
                            final inc = _incidents[i];
                            return Card(
                              child: ListTile(
                                leading: Icon(
                                  inc.isConfirmed ? Icons.warning_amber : Icons.sensors,
                                  color: inc.isConfirmed ? Colors.red : Colors.orange,
                                ),
                                title: Text(inc.cameraName ?? 'Kamera #${inc.cameraId}'),
                                subtitle: Text('${inc.status} • ${inc.detectedAt != null ? _formatDate(inc.detectedAt!) : '-'}'),
                                trailing: const Icon(Icons.chevron_right),
                                onTap: () => context.push(AppRouter.incidentDetailPath(inc.id)),
                              ),
                            );
                          },
                        ),
                ),
    );
  }

  String _formatDate(DateTime d) {
    return '${d.day}.${d.month}.${d.year} ${d.hour}:${d.minute.toString().padLeft(2, '0')}';
  }
}
