import 'package:flutter/material.dart';
import 'package:flamescope/core/constants/app_constants.dart';

const _monthLabels = <String>[
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

String formatIncidentDate(DateTime date) {
  final month = _monthLabels[date.month - 1];
  final hour = date.hour.toString().padLeft(2, '0');
  final minute = date.minute.toString().padLeft(2, '0');
  return '${date.day} $month ${date.year} • $hour:$minute';
}

String statusLabel(String status) {
  switch (status.toUpperCase()) {
    case 'DETECTED':
      return 'DETECTED';
    case 'CONFIRMED':
      return 'CONFIRMED';
    case 'DISMISSED':
      return 'DISMISSED';
    default:
      return status;
  }
}

Color statusColor(String status) {
  switch (status.toUpperCase()) {
    case 'CONFIRMED':
      return Colors.green;
    case 'DISMISSED':
      return Colors.grey;
    case 'DETECTED':
    default:
      return Colors.orange;
  }
}

class StatusBadge extends StatelessWidget {
  const StatusBadge({
    super.key,
    required this.status,
    this.compact = false,
  });

  final String status;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(status);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 10,
        vertical: compact ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        border: Border.all(color: color.withValues(alpha: 0.45)),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: compact ? 7 : 8, color: color),
          SizedBox(width: compact ? 5 : 6),
          Text(
            statusLabel(status),
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: compact ? 11 : 12,
            ),
          ),
        ],
      ),
    );
  }
}

Color roleColor(AppRole role) {
  switch (role) {
    case AppRole.admin:
      return Colors.red;
    case AppRole.manager:
      return Colors.deepOrange;
    case AppRole.employee:
      return Colors.blue;
    case AppRole.fireResponseUnit:
      return Colors.green;
  }
}

class RoleBadge extends StatelessWidget {
  const RoleBadge({
    super.key,
    required this.role,
    this.compact = false,
  });

  final AppRole role;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final color = roleColor(role);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 10,
        vertical: compact ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.09),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        role.label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: compact ? 11 : 12,
        ),
      ),
    );
  }
}
