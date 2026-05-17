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
            Row(
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE0B2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.analytics_outlined,
                    color: Color(0xFFE65100),
                    size: 20,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Alarm Summary',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 2.35,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              children: [
                _MetricTile(
                  icon: Icons.warning_amber,
                  label: 'Total',
                  value: '${data['total'] ?? 0}',
                  color: const Color(0xFFE65100),
                  background: const Color(0xFFFFF3E0),
                ),
                _MetricTile(
                  icon: Icons.verified,
                  label: 'Confirmed',
                  value: '${data['confirmed'] ?? 0}',
                  color: const Color(0xFF2E7D32),
                  background: const Color(0xFFE8F5E9),
                ),
                _MetricTile(
                  icon: Icons.close,
                  label: 'False Alarm',
                  value: '${data['dismissed'] ?? 0}',
                  color: const Color(0xFF6D4C41),
                  background: const Color(0xFFFFF8E1),
                ),
                _MetricTile(
                  icon: Icons.percent,
                  label: 'Avg. Risk',
                  value: avgRisk == null ? '-' : '%${(avgRisk * 100).round()}',
                  color: const Color(0xFFC62828),
                  background: const Color(0xFFFFEBEE),
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
    required this.background,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: background,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    value,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: const Color(0xFF30221B),
                        ),
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
