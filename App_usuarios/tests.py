{% extends 'App_usuarios/C_base.html' %}

{% block title %}Inicio - Leidy Make Up{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto space-y-6">

  <!-- BANNER DE BIENVENIDA -->
  <div class="relative bg-gradient-to-r from-rose-700 via-rose-600 to-pink-500 rounded-3xl p-8 text-white shadow-lg shadow-rose-200/40 overflow-hidden">
    <div class="absolute -right-8 -top-8 w-44 h-44 rounded-full bg-white/10 blur-2xl pointer-events-none"></div>
    <div class="absolute right-20 -bottom-10 w-36 h-36 rounded-full bg-pink-400/20 blur-xl pointer-events-none"></div>

    <span class="text-xs font-medium text-rose-100 uppercase tracking-wide">Bienvenida</span>
    <h2 class="text-2xl sm:text-3xl font-bold mt-1 mb-2 flex items-center gap-2">
      Hola, {{ request.session.nombre_usuario|default:"Adrian" }} 💕
    </h2>
    <p class="text-xs sm:text-sm text-rose-100 max-w-lg mb-6 leading-relaxed">
      Reserva tu próxima cita en Leidy Make Up. Elige el servicio, el día y la hora que mejor te funcione.
    </p>

    <!-- BOTONES DE ACCIÓN -->
    <div class="flex flex-wrap gap-3">
      <a href="{% url 'App_agenda:c_reservar' %}" class="px-5 py-2.5 bg-white text-rose-700 rounded-xl text-xs font-bold shadow-sm hover:bg-rose-50 transition-all flex items-center gap-2">
        <i data-lucide="calendar-plus" class="w-4 h-4"></i> Reservar cita
      </a>
      <a href="{% url 'App_agenda:c_mis_citas' %}" class="px-5 py-2.5 bg-rose-800/40 hover:bg-rose-800/60 border border-white/20 text-white rounded-xl text-xs font-semibold backdrop-blur-sm transition-all flex items-center gap-2">
        <i data-lucide="calendar" class="w-4 h-4"></i> Mis citas
      </a>
    </div>
  </div>

  <!-- TARJETA DE NOTIFICACIÓN -->
  <div class="bg-white rounded-2xl p-4 border border-rose-100/80 shadow-sm flex items-center gap-4">
    <div class="w-10 h-10 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shrink-0">
      <i data-lucide="bell" class="w-5 h-5"></i>
    </div>
    <div>
      <h3 class="text-xs font-semibold text-gray-800">Tienes 1 notificación sin leer</h3>
      <p class="text-[11px] text-gray-400">Revisa tus mensajes</p>
    </div>
  </div>

  <!-- TARJETAS DE ACCESOS DIRECTOS (GRID 3 COLUMNAS) -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

    <!-- Tarjeta Servicios -->
    <a href="{% url 'App_servicios:lista' %}" class="bg-white rounded-2xl p-6 border border-rose-100/80 shadow-sm hover:shadow-md hover:border-rose-300 transition-all group">
      <div class="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <i data-lucide="sparkles" class="w-5 h-5"></i>
      </div>
      <h3 class="text-sm font-bold text-gray-900 mb-1">Servicios</h3>
      <p class="text-xs text-gray-400">Explora nuestro catálogo de servicios.</p>
    </a>

    <!-- Tarjeta Reservar cita -->
    <a href="{% url 'App_agenda:c_reservar' %}" class="bg-white rounded-2xl p-6 border border-rose-100/80 shadow-sm hover:shadow-md hover:border-rose-300 transition-all group">
      <div class="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <i data-lucide="calendar-plus" class="w-5 h-5"></i>
      </div>
      <h3 class="text-sm font-bold text-gray-900 mb-1">Reservar cita</h3>
      <p class="text-xs text-gray-400">Selecciona servicio, día y hora.</p>
    </a>

    <!-- Tarjeta Mensajes -->
    <a href="{% url 'App_agenda:c_mensajes' %}" class="bg-white rounded-2xl p-6 border border-rose-100/80 shadow-sm hover:shadow-md hover:border-rose-300 transition-all group">
      <div class="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        <i data-lucide="message-square" class="w-5 h-5"></i>
      </div>
      <h3 class="text-sm font-bold text-gray-900 mb-1">Mensajes</h3>
      <p class="text-xs text-gray-400">Conversaciones con tu estilista.</p>
    </a>

  </div>

</div>
{% endblock %}