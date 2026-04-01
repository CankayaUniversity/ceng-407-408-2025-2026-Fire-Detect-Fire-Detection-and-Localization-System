// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';

int _viewCounter = 0;

/// RTSP URL'ini MediaMTX HLS URL'ine dönüştür.
/// rtsp://IP:8554/stream  →  http://IP:8888/stream
String rtspToHls(String rtspUrl) {
  try {
    final clean = rtspUrl.replaceAll('"', '').trim();
    final uri = Uri.parse(clean);
    return 'http://${uri.host}:8888${uri.path.isEmpty ? '/stream' : uri.path}';
  } catch (_) {
    return rtspUrl;
  }
}

class HlsPlayerWidget extends StatefulWidget {
  const HlsPlayerWidget({super.key, required this.rtspUrl});
  final String rtspUrl;

  @override
  State<HlsPlayerWidget> createState() => _HlsPlayerWidgetState();
}

class _HlsPlayerWidgetState extends State<HlsPlayerWidget> {
  late final String _viewId;

  @override
  void initState() {
    super.initState();
    _viewId = 'hls-player-${_viewCounter++}';
    final hlsUrl = rtspToHls(widget.rtspUrl);

    ui_web.platformViewRegistry.registerViewFactory(_viewId, (int id) {
      final iframe = html.IFrameElement()
        ..src = hlsUrl
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..allowFullscreen = true
        ..setAttribute('allow', 'autoplay; fullscreen');
      return iframe;
    });
  }

  @override
  Widget build(BuildContext context) {
    return HtmlElementView(viewType: _viewId);
  }
}
