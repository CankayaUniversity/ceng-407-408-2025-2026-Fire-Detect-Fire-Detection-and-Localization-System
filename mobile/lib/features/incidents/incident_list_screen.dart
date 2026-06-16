import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/utils/display_formatters.dart';
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
      final list = (r.data['incidents'] as List?)
              ?.map((e) => IncidentModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      if (mounted)
        setState(() {
          _incidents = list;
          _loading = false;
        });
    } catch (e) {
      if (mounted)
        setState(() {
          _error = e is DioException
              ? (e.response?.statusMessage ?? 'Connection error')
              : 'Could not load';
          _loading = false;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Incidents'),
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
                      FilledButton(
                          onPressed: _load, child: const Text('Retry')),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _incidents.isEmpty
                      ? const Center(child: Text('No incidents found'))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _incidents.length,
                          itemBuilder: (context, i) {
                            final inc = _incidents[i];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 10),
                              child: ListTile(
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 8,
                                ),
                                leading: Container(
                                  width: 42,
                                  height: 42,
                                  decoration: BoxDecoration(
                                    color: _incidentColor(inc)
                                        .withValues(alpha: 0.10),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Icon(
                                    inc.isDismissed
                                        ? Icons.cancel_outlined
                                        : inc.isConfirmed
                                            ? Icons.local_fire_department
                                            : Icons.sensors,
                                    color: _incidentColor(inc),
                                  ),
                                ),
                                title: Text(
                                  inc.cameraName ?? 'Camera #${inc.cameraId}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                subtitle: Padding(
                                  padding: const EdgeInsets.only(top: 8),
                                  child: Wrap(
                                    crossAxisAlignment:
                                        WrapCrossAlignment.center,
                                    spacing: 8,
                                    runSpacing: 6,
                                    children: [
                                      StatusBadge(
                                        status: inc.status,
                                        compact: true,
                                      ),
                                      Text(
                                        inc.detectedAt != null
                                            ? formatIncidentDate(
                                                inc.detectedAt!,
                                              )
                                            : '-',
                                      ),
                                      if (inc.isDismissed)
                                        const Text(
                                          'False Alarm',
                                          style: TextStyle(
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                                trailing: const Icon(Icons.chevron_right),
                                onTap: () => context
                                    .push(AppRouter.incidentDetailPath(inc.id)),
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}

Color _incidentColor(IncidentModel incident) {
  if (incident.isDismissed) return Colors.grey;
  if (incident.isConfirmed) return const Color(0xFFC62828);
  return const Color(0xFFE65100);
}
