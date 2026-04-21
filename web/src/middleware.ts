// middleware.ts
import { jwtDecode } from 'jwt-decode'
import { NextRequest, NextResponse } from 'next/server'
import { Role } from './schemas/users/constants'
import { AUTH_COOKIE_NAME, DecodedToken } from './utils/clientCookie'

enum WhenAuthenticated {
  REDIRECT = 'redirect',
  NEXT = 'next',
}

// Use regex para rotas dinâmicas
const publicRoutes = [
  {
    pattern: /^\/login$/,
    whenAuthenticated: WhenAuthenticated.REDIRECT,
  },
  {
    pattern: /^\/cadastro$/,
    whenAuthenticated: WhenAuthenticated.REDIRECT,
  },
  {
    pattern: /^\/$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/noticias(\/.*)?$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/ranking(\/.*)?$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/modelos-negocio(\/.*)?$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/mercado$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/termos$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
  {
    pattern: /^\/quiz(\/.*)?$/,
    whenAuthenticated: WhenAuthenticated.NEXT,
  },
] as const

const privateRoutes = [
  {
    pattern: /^\/admin(\/.*)?$/,
    whenAuthenticated: 'next',
    necessaryRole: Role.ADMIN,
  },
  // /franqueador (root): qualquer logado — page redireciona pra /minhas-franquias
  {
    pattern: /^\/franqueador$/,
    whenAuthenticated: 'next',
  },
  // /franqueador/minhas-franquias: qualquer logado pode cadastrar marca
  {
    pattern: /^\/franqueador\/minhas-franquias$/,
    whenAuthenticated: 'next',
  },
  // Outros subpaths de /franqueador: exige role FRANCHISOR
  {
    pattern: /^\/franqueador(\/.*)?$/,
    whenAuthenticated: 'next',
    necessaryRole: Role.FRANCHISOR,
  },
  {
    pattern: /^\/perfil$/,
    whenAuthenticated: 'next',
  },
] as const satisfies ReadonlyArray<{
  pattern: RegExp
  whenAuthenticated: 'next'
  necessaryRole?: Role | Role[]
}>

const REDIRECT_WHEN_NOT_AUTHENTICATED = '/login'

function buildRedirectUrl(request: NextRequest, pathname: string): URL {
  const forwardedHost = request.headers.get('x-forwarded-host')
  const forwardedProto = request.headers.get('x-forwarded-proto')

  if (forwardedHost && forwardedProto) {
    return new URL(pathname, `${forwardedProto}://${forwardedHost}`)
  }

  const url = request.nextUrl.clone()
  url.pathname = pathname
  return url
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  const publicRoute = publicRoutes.find((route) => route.pattern.test(pathname))
  const privateRoute = privateRoutes.find((route) =>
    route.pattern.test(pathname),
  )
  const authToken = request.cookies.get(AUTH_COOKIE_NAME)

  // Não autenticado e rota pública
  if (!authToken && publicRoute) {
    return NextResponse.next()
  }

  // Não autenticado e rota privada
  if (!authToken && !publicRoute) {
    return NextResponse.redirect(
      buildRedirectUrl(request, REDIRECT_WHEN_NOT_AUTHENTICATED),
    )
  }

  // Autenticado e rota pública que redireciona
  if (
    authToken &&
    publicRoute &&
    publicRoute.whenAuthenticated === WhenAuthenticated.REDIRECT
  ) {
    return NextResponse.redirect(buildRedirectUrl(request, '/'))
  }

  // Autenticado e rota privada
  if (authToken && privateRoute) {
    const token = request.cookies.get(AUTH_COOKIE_NAME)?.value as string
    const decodedToken: DecodedToken = jwtDecode(token)

    if (decodedToken.exp && decodedToken.exp < Date.now() / 1000) {
      return NextResponse.redirect(
        buildRedirectUrl(request, REDIRECT_WHEN_NOT_AUTHENTICATED),
      )
    }

    if ('necessaryRole' in privateRoute && privateRoute.necessaryRole) {
      const userRole = decodedToken.role as Role | undefined
      const necessaryRoles = (
        Array.isArray(privateRoute.necessaryRole)
          ? privateRoute.necessaryRole
          : [privateRoute.necessaryRole]
      ) as ReadonlyArray<Role>

      if (!userRole || !necessaryRoles.includes(userRole)) {
        return NextResponse.redirect(buildRedirectUrl(request, '/'))
      }
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|assets|uploads|favicon.ico).*)'],
}
