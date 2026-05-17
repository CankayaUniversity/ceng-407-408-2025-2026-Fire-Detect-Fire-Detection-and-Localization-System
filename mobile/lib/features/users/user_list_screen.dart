import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:dio/dio.dart';
import 'package:flamescope/core/api/api_client.dart';
import 'package:flamescope/core/auth/auth_service.dart';
import 'package:flamescope/core/constants/app_constants.dart';
import 'package:flamescope/core/constants/api_constants.dart';
import 'package:flamescope/core/router/app_router.dart';
import 'package:flamescope/core/utils/display_formatters.dart';
import 'package:flamescope/shared/models/user_model.dart';

class UserListScreen extends StatefulWidget {
  const UserListScreen({super.key});

  @override
  State<UserListScreen> createState() => _UserListScreenState();
}

class _UserListScreenState extends State<UserListScreen> {
  List<UserModel> _users = [];
  bool _loading = true;
  String? _error;
  bool _showInactiveUsers = false;

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
    final role = auth.user?.role;
    if (role != AppRole.admin) {
      setState(() {
        _loading = false;
        _error = 'Only admins can access this page.';
      });
      return;
    }
    final dio = createDio(auth);
    try {
      final r = await dio.get(ApiEndpoints.users);
      final list = (r.data['users'] as List?)
              ?.map((e) => UserModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      if (mounted) {
        setState(() {
          _users = list;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e is DioException
              ? (e.response?.statusMessage ?? 'Connection error')
              : 'Could not load';
          _loading = false;
        });
      }
    }
  }

  Future<void> _confirmDeactivate(BuildContext context, UserModel u) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Deactivate User'),
        content: Text(
          '${u.fullName} (${u.email}) account? They will not be able to sign in.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Deactivate'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    await _deactivate(u.id);
  }

  Future<void> _deactivate(int userId) async {
    final auth = context.read<AuthService>();
    final dio = createDio(auth);
    try {
      await dio.patch(ApiEndpoints.userDeactivate(userId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User deactivated')),
        );
        _load();
      }
    } catch (e) {
      if (mounted) _showErrorSnackBar(e);
    }
  }

  Future<void> _reactivate(int userId) async {
    final auth = context.read<AuthService>();
    final dio = createDio(auth);
    try {
      await dio.patch(ApiEndpoints.userReactivate(userId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User reactivated')),
        );
        _load();
      }
    } catch (e) {
      if (mounted) _showErrorSnackBar(e);
    }
  }

  void _showErrorSnackBar(dynamic e) {
    final msg = e is DioException
        ? (e.response?.data is Map &&
                (e.response?.data as Map)['detail'] != null
            ? (e.response?.data as Map)['detail'].toString()
            : e.response?.statusMessage ?? 'Operation failed')
        : 'Operation failed';
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Widget _buildUserList() {
    final active = _users.where((u) => u.isActive).toList();
    final inactive = _users.where((u) => !u.isActive).toList();
    final currentUser = context.read<AuthService>().user;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SwitchListTile(
            value: _showInactiveUsers,
            onChanged: (v) => setState(() => _showInactiveUsers = v),
            title: const Text('Show inactive users'),
          ),
          const SizedBox(height: 8),
          if (!_showInactiveUsers) ...[
            if (active.isEmpty)
              const Center(
                  child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No active users'),
              ))
            else
              ...active.map((u) => _userCard(context, u, currentUser)),
          ] else ...[
            if (active.isEmpty && inactive.isEmpty)
              const Center(
                  child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No users'),
              ))
            else ...[
              if (active.isNotEmpty) ...[
                const Padding(
                  padding: EdgeInsets.only(top: 8, bottom: 4),
                  child: Text('Active Users',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      )),
                ),
                ...active.map((u) => _userCard(context, u, currentUser)),
              ],
              if (inactive.isNotEmpty) ...[
                const Padding(
                  padding: EdgeInsets.only(top: 16, bottom: 4),
                  child: Text('Inactive Users',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      )),
                ),
                ...inactive.map((u) => _userCard(context, u, currentUser)),
              ],
            ],
          ],
        ],
      ),
    );
  }

  Widget _userCard(BuildContext context, UserModel u, UserModel? currentUser) {
    final canDeactivate = currentUser != null &&
        currentUser.id != u.id &&
        u.role != AppRole.admin &&
        u.isActive;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          u.isActive ? Icons.person_outline : Icons.person_off_outlined,
          color: u.isActive ? null : Colors.grey,
        ),
        title: Text(u.fullName),
        subtitle: Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(u.email),
            RoleBadge(role: u.role, compact: true),
            if (!u.isActive)
              const Text(
                'Inactive',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
          ],
        ),
        trailing: canDeactivate
            ? TextButton(
                onPressed: () => _confirmDeactivate(context, u),
                child: const Text('Deactivate'),
              )
            : !u.isActive
                ? TextButton(
                    onPressed: () => _reactivate(u.id),
                    child: const Text('Reactivate'),
                  )
                : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('User Management'),
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
                        onPressed: _load,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _buildUserList(),
      floatingActionButton: _error == null && !_loading
          ? FloatingActionButton(
              onPressed: () async {
                final created = await context.push<bool>(AppRouter.userCreate);
                if (created == true && mounted) _load();
              },
              child: const Icon(Icons.add),
            )
          : null,
    );
  }
}
