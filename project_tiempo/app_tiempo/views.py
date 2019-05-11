from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.models import User
from project_tiempo import settings
from . import parser
from .models import Municipio, Preferencia, Comentario, Municipio_Usuario
import datetime

global filtro_max
filtro_max = None
global filtro_min
filtro_min = None


def logout_user(request):
    print('Voy a hacerle logout')
    logout(request)

def login_user(request):
    usuario = request.POST['usuario']
    contraseña = request.POST['contraseña']
    user = authenticate(username=usuario, password=contraseña)
    if user:
        login(request, user)

def add_seleccion_usuario(request, municipio_inBD):
    print('Voy a ver si lo añado a la selección de este usuario')
    # Compruebo si ya existe esta asignación
    usuario = User.objects.get(username=request.user.username)
    municipio_usuario = Municipio_Usuario.objects.filter(usuario=usuario).filter(municipio=municipio_inBD)
    if not municipio_usuario:
        print('No tiene la asinación hecha, lo añado')
        municipio_usuario = Municipio_Usuario(usuario = usuario,
                                              municipio = municipio_inBD,
                                              fecha = datetime.date.today(),
                                              )
        municipio_usuario.save()
    else:
        print('Ya estaba asignado')


def add_municipio(request):

    municipio = request.POST['municipio']
    print('Nuevo municipio recibido para asignar: ' + municipio)

    try: # Compruebo si existe el municipio
        id = settings.municipios[municipio]['id'][-5:]
        municipio_inBD = Municipio.objects.get(nombre=municipio)
        mensaje = "El municipio ya existe en la BD de municipios"
        add_seleccion_usuario(request, municipio_inBD)
    except KeyError: # No es un municipio válido.
        mensaje = "Disculpe, el municipio introducido no existe"
    except Municipio.DoesNotExist: # Es un municipio válido y nuevo.
        info = parser.get_info(id)
        print('Este es su id: ' + id)
        # Añadir este Municipio a la Base de datos municipio

        new_mun = Municipio(nombre = info['nombre'],
                            mun_id = id,
                            altitud = settings.municipios[municipio]['altitud'],
                            latitud = settings.municipios[municipio]['latitud'],
                            longitud = settings.municipios[municipio]['longitud'],
                            maxima = info['maxima'],
                            minima = info['minima'],
                            prob_precipitacion = info['prob_precipitacion'],
                            descripcion = info['estado_cielo'],
                            url = settings.municipios[municipio]['url'],
                            num_comentarios = 0,
                            )
        new_mun.save()
        mensaje = "Añadido " + municipio + " a su lista de municipios"

        add_seleccion_usuario(request, new_mun)

    return mensaje

def actualizar_municipio(id):
    print('Actualizo la info del municipio')

    # Sé que va a estar en mi BD porque ya he hecho la
    # comprobación en la view anterior.
    municipio_inBD = Municipio.objects.get(mun_id = id)
    info_nueva = parser.get_info(id)
    print('La info  nueva que recibo: ' + str(info_nueva['estado_cielo']))
    municipio_inBD.maxima = info_nueva['maxima']
    municipio_inBD.minima = info_nueva['minima']
    municipio_inBD.prob_precipitacion = info_nueva['prob_precipitacion']
    municipio_inBD.descripcion = info_nueva['estado_cielo']

    municipio_inBD.save()

def borrar_municipio(request):
    municipio = request.POST['municipio']
    municipio_inBD = Municipio.objects.get(nombre = municipio)
    usuario = User.objects.get(username=request.user.username)
    municipio_usuario = Municipio_Usuario.objects.filter(usuario = usuario).filter(municipio = municipio_inBD)
    municipio_usuario.delete()
    print('quiere eliminar un municipio: ' + municipio)


def cambiar_titulo(request):
    nuevo_titulo = request.POST['titulo']
    print('El nuevo titulo que quiere es: ' + nuevo_titulo)

    # Este POST me llega solo cuando estoy autenticado si o si.
    usuario = User.objects.get(username=request.user.username)
    print('Voy a cambiarle el titulo a: ' + str(usuario))

    try:
        # Compruebo si ya tiene algo asignado este usuario.
        preferencia = Preferencia.objects.get(usuario=usuario)
    except Preferencia.DoesNotExist:
        print('Aún no existe, creo el  nuevo modelo')
        preferencia = Preferencia(usuario=usuario)

    preferencia.titulo = nuevo_titulo
    preferencia.save()
    mensaje = "Enhorabuena! Has cambiado el título de tu página"
    return mensaje

def add_comentario(request, id):
    comentario = request.POST['mensaje']
    print('Añado el comentario: ' + comentario)

    try:
        municipio = Municipio.objects.get(mun_id = id)
        usuario = User.objects.get(username=request.user.username)

        new_coment = Comentario(municipio = municipio,
                                comentario = comentario,
                                usuario = usuario,
                                fecha = datetime.date.today(),
                                )
        new_coment.save()
        print('Comentario guardado')

        num_comentarios = municipio.num_comentarios
        print('Comentarios que tiene actualmente: ' + str(num_comentarios))
        num_comentarios = num_comentarios + 1
        municipio.num_comentarios = num_comentarios
        municipio.save()

    # A este caso nunca va a llegar, porque ya lo controlo antes.
    # Lo pongo por si acaso.
    except Municipio.DoesNotExist:
        print('Recibo un comentario, pero lo no guardo porque' +
              ' ese municipio no ha sido seleccionado por ningun usuario')

def filtro_temp(filtro_max,filtro_min):
    municipios = Municipio.objects.all()
    lista_municipios = []

    print('maxima que recibo: ' + str(filtro_max))
    print('minima que recibo: ' + str(filtro_min))


    if filtro_max and filtro_min:
        print('Recibo maxima y minima')
        for municipio in municipios:
            # Para manejar el caso de que no haya conexión.
            if municipio.maxima == None or municipio.minima == None:
                continue
            if municipio.maxima <= int(filtro_max) and municipio.maxima >= int(filtro_min):
                lista_municipios.append(municipio)
    elif filtro_max:
        print('Recibo solo maxima')
        for municipio in municipios:
            if municipio.maxima == None or municipio.minima == None:
                continue
            if municipio.maxima <= int(filtro_max):
                lista_municipios.append(municipio)
    elif filtro_min:
        print('Recibo solo minima')
        for municipio in municipios:
            if municipio.maxima == None or municipio.minima == None:
                continue
            if municipio.maxima>= int(filtro_min):
                lista_municipios.append(municipio)

    return lista_municipios

########################################################################
# Create your views here.

def main(request):

    if request.method == "POST":
        form_type = request.POST['form_type']
        if form_type == 'logout':
            logout_user(request)
        elif form_type == 'login':
            login_user(request)

    usuarios = User.objects.all()
    titulos = {}
    for usuario in usuarios:
        try:
            preferencia = Preferencia.objects.get(usuario=usuario)
            titulos[usuario] = preferencia.titulo
        except Preferencia.DoesNotExist:
            titulos[usuario] = "Página de " + str(usuario)

    municipios = Municipio.objects.all()
    municipios_comentados = [] # Lista de municipios que tienen algún comentario
    for municipio in municipios:
        if municipio.num_comentarios:
            municipios_comentados.append(municipio)

    # Lista de municipios solo que tienen comentarios, en orden decreciente.
    municipios_comentados.sort(key=lambda Municipio: Municipio.num_comentarios, reverse=True)

    return(render(request, './main.html', {'usuarios': usuarios,
                                           'titulos': titulos,
                                           'municipios_comentados': municipios_comentados}))

def usuario(request, user_path):
    mensaje = ""

    if request.method == "GET":
        try:
            user = User.objects.get(username=user_path)
            print('El usuario existe')
            content = "Mi lista de municipios"
        except User.DoesNotExist:
            user = None
            print('El usuario no está registrado, no tendrá contenido')
            content = "Este usuario no está registrado."

    elif request.method == "POST":
        form_type = request.POST['form_type']
        if form_type == 'logout':
            logout_user(request)
        elif form_type == 'login':
            login_user(request)
        elif form_type == 'css':
            print('Quiere cambiar el css')
        elif form_type == 'titulo':
            print('Quiere cambiar su titulo')
            mensaje = cambiar_titulo(request)
        elif form_type == 'municipio':
            mensaje = add_municipio(request)
        elif form_type == 'quitar':
            borrar_municipio(request)
    try:
        user = User.objects.get(username=user_path)
    except User.DoesNotExist:
        user = None
    lista_municipios_user = Municipio_Usuario.objects.filter(usuario=user).order_by('-id')
    try:
        preferencias = Preferencia.objects.filter(usuario=user)[0]
    except:
        # Maneja el caso de que el usuario aún no haya establecido ninguna preferencia.
        preferencias = []

    # El filtro me devuelve una lista. Me quedo con el primer elemento,
    # que será el único que corresponda con ese nombre.
    return render(request, './usuario.html', {'path': user_path,
                                              'mensaje': mensaje,
                                              'lista_municipios_user': lista_municipios_user,
                                              'preferencias': preferencias})

def municipios(request):

    global filtro_max
    global filtro_min

    lista_municipios = Municipio.objects.all()

    if request.method == "POST":
        form_type = request.POST['form_type']
        if form_type == 'logout':
            logout_user(request)
        elif form_type == 'login':
            login_user(request)
        elif form_type == 'filtro_temp':
            print('Quiere filtrar la temperatura')
            filtro_max = request.POST['maxima']
            filtro_min = request.POST['minima']

    elif request.method == "GET":
        filtro_max = None
        filtro_min = None
        lista_municipios = Municipio.objects.all()


    # Para evitar que al hacer el logout sobre un filtro
    # me vuelvan a aparecer todos los municipios
    if filtro_max or filtro_min:
        lista_municipios = filtro_temp(filtro_max,filtro_min)

    return render(request, './municipios.html', {'lista_municipios': lista_municipios,
                                                 'filtro_max': filtro_max,
                                                 'filtro_min': filtro_min})

def municipios_id(request, id):


    if request.method == "POST":
        form_type = request.POST['form_type']
        if form_type == 'logout':
            logout_user(request)
        elif form_type == 'login':
            login_user(request)
        elif form_type == 'comentario':
            add_comentario(request, id)

    try:
        print('Voy a comprobar si tengo en mi BD el municipio con id: ' + str(id))
        municipio = Municipio.objects.get(mun_id=id)

        # Si me hacen un GET actualizo la info.
        if request.method == "GET":
            actualizar_municipio(id)

        # Tras haber actualizado la info en la BD, recupero
        # la info actualizada
        municipio = Municipio.objects.get(mun_id=id)

        # Sea GET o POST, muestro la info.
        url = settings.municipios[municipio.nombre]['url']
        lista_comentarios = Comentario.objects.filter(municipio=municipio)
        print('Está en mi BD')
    except Municipio.DoesNotExist:
        # /municipio/id => Ese id no lo tengo en mi BD (nadie lo ha seleccionado)
        municipio = ""
        lista_comentarios = {}
        print('No está en mi BD')

    return render(request, './municipiosID.html', {'municipio': municipio,
                                                   'lista_comentarios': lista_comentarios})


def info(request):

    if request.method == "POST":
        form_type = request.POST['form_type']
        if form_type == 'logout':
            logout_user(request)
        elif form_type == 'login':
            login_user(request)

    return render(request, './info.html')

def favicon(request):
    return HttpResponseRedirect('/')