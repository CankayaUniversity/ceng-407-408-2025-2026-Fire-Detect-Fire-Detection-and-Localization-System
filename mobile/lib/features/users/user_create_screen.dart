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

class UserCreateScreen extends StatefulWidget {
  const UserCreateScreen({super.key});

  @override
  State<UserCreateScreen> createState() => _UserCreateScreenState();
}

class _UserCreateScreenState extends State<UserCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _fullNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  AppRole _selectedRolee = AppRole.employee;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _fullNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    if (auth.user?.role != AppRole.admin) {
      setState(() {
        _loading = false;
        _error = 'You are not authorized for this action.';
      });
      return;
    }
    final dio = createDio(auth);
    try {
      await dio.post(
        ApiEndpoints.users,
        data: {
          'full_name': _fullNameController.text.trim(),
          'email': _emailController.text.trim(),
          'password': _passwordController.text,
          'role': _selectedRolee.value,
        },
      );
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User created')),
        );
        context.pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e is DioException
              ? (e.response?.data is Map &&
                      (e.response?.data as Map)['detail'] != null
                  ? (e.response?.data as Map)['detail'].toString()
                  : e.response?.statusMessage ?? 'Request failed')
              : 'Request failed';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('New User'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _fullNameController,
                decoration: const InputDecoration(
                  labelText: 'Full Name',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person_outline),
                ),
                textInputAction: TextInputAction.next,
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Enter full name' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _emailController,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.email_outlined),
                ),
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Email girin';
                  if (!v.contains('@')) return 'Enter a valid email';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _passwordController,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock_outline),
                ),
                obscureText: true,
                textInputAction: TextInputAction.done,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Enter a password';
                  if (v.length < 6) return 'Must be at least 6 characters';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<AppRole>(
                value: _selectedRolee,
                decoration: const InputDecoration(
                  labelText: 'Role',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.badge_outlined),
                ),
                items: AppRole.values
                    .map((r) => DropdownMenuItem(
                          value: r,
                          child: RoleBadge(role: r, compact: true),
                        ))
                    .toList(),
                onChanged: (v) {
                  if (v != null) setState(() => _selectedRolee = v);
                },
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Create'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
