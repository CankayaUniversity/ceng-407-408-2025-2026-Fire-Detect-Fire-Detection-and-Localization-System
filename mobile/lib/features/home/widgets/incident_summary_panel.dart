import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class IncidentSummaryPanel extends StatefulWidget {
  const IncidentSummaryPanel({super.key});

  @override
  State<IncidentSummaryPanel> createState() => _IncidentSummaryPanelState();
}

class _IncidentSummaryPanelState extends State<IncidentSummaryPanel> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final dio = createDio(context.read<AuthService>());
    final response = await dio.get(ApiEndpoints.incidentSummary);
    return response.data as Map<String, dynamic>;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const SizedBox(
            height: 96,
            child: Center(child: CircularProgressIndicator()),
          );
        }

        final data = snapshot.data!;
        final avgRisk = (data['average_risk'] as num?)?.toDouble();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Alarm Ozeti',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 2.5,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                _MetricTile(
                  icon: Icons.warning_amber,
                  label: 'Toplam',
                  value: '${data['total'] ?? 0}',
                  color: Colors.deepOrange,
                ),
                _MetricTile(
                  icon: Icons.verified,
                  label: 'Onaylanan',
                  value: '${data['confirmed'] ?? 0}',
                  color: Colors.green,
                ),
                _MetricTile(
                  icon: Icons.close,
                  label: 'Yanlis Alarm',
                  value: '${data['dismissed'] ?? 0}',
                  color: Colors.brown,
                ),
                _MetricTile(
                  icon: Icons.percent,
                  label: 'Ort. Risk',
                  value: avgRisk == null ? '-' : '%${(avgRisk * 100).round()}',
                  color: Colors.indigo,
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    value,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
