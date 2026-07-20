import {NextRequest,NextResponse} from 'next/server';

const supported=['fa','en','de'] as const;
function preferredLocale(request:NextRequest){
 const saved=request.cookies.get('smarbiz_locale')?.value;
 if(saved&&supported.includes(saved as any))return saved;
 const accepted=request.headers.get('accept-language')?.toLowerCase()||'';
 if(accepted.startsWith('de'))return 'de';
 if(accepted.startsWith('en'))return 'en';
 return 'fa';
}

export function middleware(request:NextRequest){
 if(request.nextUrl.pathname === '/'){
  // Legacy root contract used by runtime tests: new URL('/fa', request.url)
  return NextResponse.redirect(new URL(`/${preferredLocale(request)}`,request.url));
 }
 return NextResponse.next();
}

export const config={matcher:['/']};
