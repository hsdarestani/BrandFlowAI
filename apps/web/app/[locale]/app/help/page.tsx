'use client';

import {use,useMemo,useState} from 'react';
import Link from 'next/link';
import {AppShell} from '@/components/app-shell';

type Action={label:string;href:string};
type Article={
 id:string;
 title:string;
 summary:string;
 purpose:string;
 steps:string[];
 tips:string[];
 issues:string[];
 actions:Action[];
};

type HelpCopy={
 title:string;
 subtitle:string;
 search:string;
 noResults:string;
 purpose:string;
 steps:string;
 tips:string;
 issues:string;
 actions:string;
 topicCount:string;
 articles:Article[];
};

const sharedActions={
 onboarding:'/onboarding',
 pulse:'/app/brand-pulse',
 calendar:'/app/calendar',
 studio:'/app/content-studio',
 approvals:'/app/approvals',
 integrations:'/app/integrations',
 analytics:'/app/analytics',
 settings:'/app/settings',
 admin:'/app/admin',
 campaigns:'/app/campaigns',
};

const copy:Record<string,HelpCopy>={
 fa:{
  title:'مرکز راهنما',
  subtitle:'راهنمای عملی اسماربیز؛ هر بخش دقیقاً توضیح می‌دهد چه کاری انجام می‌دهد، از کجا شروع کنید و اگر چیزی کار نکرد چه چیزی را بررسی کنید.',
  search:'جستجو در راهنما…',
  noResults:'موضوعی با این عبارت پیدا نشد.',
  purpose:'این بخش برای چیست؟',
  steps:'مراحل انجام کار',
  tips:'نکته‌های مهم',
  issues:'اگر نتیجه نگرفتید',
  actions:'رفتن به بخش مرتبط',
  topicCount:'موضوع راهنما',
  articles:[
   {
    id:'getting-started',title:'شروع کار',summary:'مسیر درست از ساخت فضای کاری تا اولین خروجی قابل استفاده.',
    purpose:'شروع خوب در اسماربیز یعنی اول اطلاعات برند را کامل کنید، بعد محصول/خدمت و کانال‌ها را مشخص کنید و فقط بعد از آن وارد تولید محتوا شوید. اگر این ترتیب رعایت نشود، خروجی AI هم اطلاعات کافی برای تصمیم‌گیری ندارد.',
    steps:['در راه‌اندازی اولیه نام برند، بازار، زبان و منطقه زمانی را ثبت کنید.','توضیح روشن کسب‌وکار، مخاطب، دردها و نتیجه مطلوب او را وارد کنید.','حداقل یک محصول یا خدمت واقعی با مزیت‌هایش اضافه کنید.','لحن برند، ستون‌های محتوا و ادعاهای ممنوع را مشخص کنید.','کانال‌هایی را که واقعاً استفاده می‌کنید انتخاب کنید و سپس تقویم یا استودیوی محتوا را باز کنید.'],
    tips:['اطلاعات دقیق و واقعی بهتر از متن طولانی و تبلیغاتی است.','اگر چند برند دارید، اطلاعات هر برند را جدا نگه دارید.','زبان اصلی محتوا روی خروجی AI و متن‌های تولیدشده اثر مستقیم دارد.'],
    issues:['اگر دکمه تولید محتوا فعال نیست، معمولاً Brand Pulse یا محصول/خدمت اصلی ناقص است.','اگر زمان‌های تقویم عجیب است، منطقه زمانی برند و پروفایل را بررسی کنید.'],
    actions:[{label:'ادامه راه‌اندازی',href:sharedActions.onboarding},{label:'تکمیل پالس برند',href:sharedActions.pulse}],
   },
   {
    id:'brand-pulse',title:'پالس برند',summary:'مرجع اصلی AI برای شناخت برند، مخاطب، پیشنهاد فروش و محدودیت‌ها.',
    purpose:'پالس برند حافظه عملیاتی اسماربیز درباره کسب‌وکار شماست. AI هنگام ساخت ایده، تقویم و محتوا از همین اطلاعات برای انتخاب زاویه، لحن، CTA و ادعاهای مجاز استفاده می‌کند.',
    steps:['خلاصه برند را طوری بنویسید که یک همکار جدید با خواندن آن بفهمد دقیقاً چه می‌فروشید.','مخاطب هدف، دردها، سؤال‌ها و نتیجه مطلوب را جداگانه وارد کنید.','برای هر محصول/خدمت توضیح، مزیت، مخاطب و در صورت وجود اعتراض‌های رایج و proof point واقعی ثبت کنید.','لحن، سبک نوشتن، ستون‌های محتوا و CTAهای ترجیحی را تکمیل کنید.','ادعاهای ممنوع و قواعد حساس برند را مشخص کنید و بعد از تغییرات مهم، اطلاعات را به‌روز نگه دارید.'],
    tips:['به‌جای «کیفیت عالی» بنویسید دقیقاً چه چیزی برای مشتری بهتر می‌شود.','فقط proof pointهایی را وارد کنید که واقعاً می‌توانید اثبات کنید.','درد مخاطب را با زبان خود مشتری بنویسید، نه با اصطلاحات داخلی شرکت.'],
    issues:['اگر خروجی‌ها عمومی و شبیه همه برندها هستند، معمولاً pain point، value proposition یا product detail کم است.','اگر AI ادعایی را نباید استفاده کند، آن را در forbidden claims یا Brand Rules صریح ثبت کنید.'],
    actions:[{label:'باز کردن پالس برند',href:sharedActions.pulse},{label:'ساخت تقویم محتوا',href:sharedActions.calendar}],
   },
   {
    id:'calendar',title:'تقویم محتوا',summary:'برنامه هفتگی AI با زاویه، فرمت، هدف، CTA و زمان انتشار.',
    purpose:'تقویم فقط لیست عنوان نیست. اسماربیز باید بر اساس Brand Pulse برای هفته یک ترکیب متنوع از آموزش، اعتمادسازی، تعامل و تبدیل بسازد و هر آیتم را به کانال و فرمت مناسب وصل کند.',
    steps:['قبل از ساخت هفته مطمئن شوید Brand Pulse و حداقل یک محصول/خدمت کامل است.','هفته موردنظر و در صورت نیاز کمپین را انتخاب کنید.','ساخت هفته را اجرا کنید و عنوان، هوک، بریف، جهت اجرای خلاقه، هدف و CTA هر آیتم را مرور کنید.','آیتم ضعیف را ویرایش یا دوباره تولید کنید؛ محتوای تأییدشده یا منتشرشده را بی‌دلیل جایگزین نکنید.','پس از نهایی‌شدن، آیتم را وارد Content Studio یا جریان تأیید کنید.'],
    tips:['تقویم خوب باید چند کار مختلف در قیف فروش انجام دهد، نه اینکه تمام هفته فروش مستقیم باشد.','برای Reel، Story و Carousel انتظار اجرای متفاوت داشته باشید؛ فقط تغییر نام فرمت کافی نیست.','اگر کمپین فعال دارید، هدف و پیشنهاد کمپین باید روی ایده‌های هفته اثر بگذارد.'],
    issues:['اگر تولید هفته خطای تنظیمات می‌دهد، ابتدا کامل‌بودن Brand Pulse و محصول را بررسی کنید.','اگر یک روز قبلاً محتوای واقعی دارد، اسماربیز نباید آن را با خروجی جدید AI خراب کند.','اگر ایده‌ها تکراری‌اند، اطلاعات مخاطب/اعتراض‌ها/ستون‌ها را دقیق‌تر کنید.'],
    actions:[{label:'باز کردن تقویم',href:sharedActions.calendar},{label:'باز کردن استودیوی محتوا',href:sharedActions.studio}],
   },
   {
    id:'content-studio',title:'استودیوی محتوا',summary:'تبدیل ایده یا آیتم تقویم به نسخه اجرایی و آماده تأیید.',
    purpose:'Content Studio جایی است که ایده خام تبدیل به محتوای قابل استفاده می‌شود. اینجا باید متن، CTA، فرمت و دارایی‌های مرتبط را تا سطحی آماده کنید که تأییدکننده دقیقاً بداند چه چیزی قرار است منتشر شود.',
    steps:['یک آیتم تقویم یا موضوع مشخص را به‌عنوان مبنا انتخاب کنید.','هدف، مخاطب، کانال و فرمت را قبل از تولید نهایی بررسی کنید.','نسخه تولیدشده را از نظر واقعیت، لحن برند، ادعاها و CTA مرور کنید.','در صورت نیاز دارایی تصویری یا فایل مرتبط را اضافه کنید.','پس از آماده‌شدن، محتوا را برای تأیید بفرستید؛ انتشار نباید قبل از تأیید نهایی انجام شود.'],
    tips:['AI را برای نوشتن نسخه نهایی بدون context رها نکنید؛ همیشه آیتم را به Brand Pulse و محصول درست متصل نگه دارید.','برای هر کانال متن و طول مناسب همان کانال را نگه دارید.','نسخه‌ای که از نظر قانونی یا تجاری حساس است باید حتماً توسط انسان مرور شود.'],
    issues:['اگر خروجی با برند نمی‌خواند، اتصال محصول/پرسونا و اطلاعات Brand Pulse را بررسی کنید.','اگر فایل یا تصویر نمایش داده نمی‌شود، ابتدا Assets و وضعیت آپلود را چک کنید.'],
    actions:[{label:'باز کردن استودیو',href:sharedActions.studio},{label:'دارایی‌ها',href:'/app/assets'}],
   },
   {
    id:'approvals',title:'جریان تأیید',summary:'ارسال محتوا برای بازبینی، ثبت نظر و جلوگیری از انتشار زودهنگام.',
    purpose:'جریان تأیید برای جداکردن «محتوای آماده» از «محتوای مجاز برای انتشار» است. این موضوع مخصوصاً برای آژانس‌ها و تیم‌های چندنفره مهم است.',
    steps:['محتوای نهایی را از Studio یا Calendar وارد وضعیت آماده تأیید کنید.','روش تأیید را انتخاب کنید: داخلی، لینک عمومی یا کانال متصل مثل Telegram/Bale.','تأییدکننده باید خود محتوا و در صورت وجود فایل‌های مرتبط را ببیند.','نظر اصلاحی را روی همان آیتم ثبت و نسخه جدید را دوباره ارسال کنید.','فقط پس از Approved شدن وارد مرحله انتشار شوید.'],
    tips:['لینک عمومی برای مشتریانی مناسب است که حساب اسماربیز ندارند.','برای هر تغییر مهم بعد از تأیید، بهتر است تأیید دوباره انجام شود.','وضعیت‌های Draft، Review، Approved و Published را با هم قاطی نکنید.'],
    issues:['اگر تأییدکننده پیام دریافت نمی‌کند، اتصال Integration مربوطه را تست کنید.','اگر لینک عمومی باز نمی‌شود، مطمئن شوید لینک همان آیتم و هنوز معتبر است.'],
    actions:[{label:'مرکز تأییدها',href:sharedActions.approvals},{label:'اتصال کانال تأیید',href:sharedActions.integrations}],
   },
   {
    id:'publishing',title:'انتشار مستقیم و کمکی',summary:'تفاوت بین انتشار از طریق API و مسیری که کاربر باید مرحله آخر را انجام دهد.',
    purpose:'همه کانال‌ها یا همه نوع حساب‌ها اجازه انتشار مستقیم API نمی‌دهند. اسماربیز بین Direct Publishing و Assisted Publishing تفاوت می‌گذارد تا وضعیت محتوا شفاف بماند.',
    steps:['در Integrations ببینید اتصال موردنظر Publishing را پشتیبانی می‌کند یا فقط handoff/approval است.','اگر Direct فعال است، دسترسی‌ها و حساب مقصد را بررسی و فقط محتوای Approved را منتشر کنید.','اگر Assisted است، متن و فایل نهایی را از اسماربیز بگیرید و مرحله انتشار را در اپ مقصد انجام دهید.','بعد از انتشار کمکی، وضعیت آیتم و در صورت امکان لینک پست را در اسماربیز ثبت کنید.'],
    tips:['Connected بودن یک Integration لزوماً به معنی اجازه Direct Publishing نیست.','محدودیت API می‌تواند بر اساس نوع حساب، کشور، مجوز یا سیاست خود پلتفرم تغییر کند.'],
    issues:['اگر دکمه انتشار مستقیم ندارید، ممکن است اتصال فقط Approval/Assisted باشد.','اگر توکن یا permission منقضی شده، اتصال را دوباره احراز هویت کنید.'],
    actions:[{label:'بررسی Integrationها',href:sharedActions.integrations},{label:'محتوای تأییدشده',href:sharedActions.approvals}],
   },
   {
    id:'telegram',title:'راه‌اندازی تلگرام',summary:'اتصال Bot برای ارسال تأییدها و پیام‌های عملیاتی.',
    purpose:'اتصال Telegram برای ارسال درخواست تأیید یا پیام‌های workflow استفاده می‌شود. برای این کار باید Bot معتبر و مقصد صحیح داشته باشید.',
    steps:['در Telegram از BotFather یک Bot بسازید و Token آن را دریافت کنید.','در Integrations اتصال Telegram را باز کنید و اطلاعات خواسته‌شده را وارد کنید.','Bot را به چت/گروه مقصد اضافه کنید و در صورت نیاز اجازه ارسال پیام بدهید.','اتصال را ذخیره و با یک پیام آزمایشی یا درخواست تأیید تست کنید.'],
    tips:['Token ربات را عمومی نکنید و داخل متن محتوا یا اسکرین‌شات به اشتراک نگذارید.','اگر گروه استفاده می‌کنید، مطمئن شوید Bot واقعاً عضو همان گروه است.'],
    issues:['خطای Unauthorized معمولاً یعنی Token اشتباه یا باطل شده است.','اگر پیام ارسال نمی‌شود ولی اتصال سالم است، chat/group مقصد و permission ربات را بررسی کنید.'],
    actions:[{label:'اتصال تلگرام',href:sharedActions.integrations},{label:'تست از تأییدها',href:sharedActions.approvals}],
   },
   {
    id:'bale-bot',title:'راه‌اندازی ربات بله',summary:'اتصال Bale Bot برای پیام و جریان تأیید.',
    purpose:'Bale Bot مشابه Telegram می‌تواند پیام‌های مربوط به تأیید و workflow را به مقصد بله ارسال کند.',
    steps:['Bot بله و Token معتبر را از مسیر رسمی بله آماده کنید.','در Integrations گزینه Bale را باز و اطلاعات اتصال را وارد کنید.','Bot را به گفت‌وگو یا گروه مقصد اضافه کنید.','اتصال را ذخیره و یک ارسال آزمایشی انجام دهید.'],
    tips:['Token را مانند رمز عبور نگه دارید.','اگر چند Bot دارید، نام نمایشی اتصال را طوری بگذارید که مقصد آن مشخص باشد.'],
    issues:['اگر API پاسخ نمی‌دهد، Token و دسترسی Bot را بررسی کنید.','اگر پیام به مقصد اشتباه می‌رود، تنظیم مقصد/شناسه گفت‌وگو را اصلاح کنید.'],
    actions:[{label:'اتصال بله',href:sharedActions.integrations},{label:'مرکز تأییدها',href:sharedActions.approvals}],
   },
   {
    id:'bale-safir',title:'راه‌اندازی بله سفیر',summary:'اتصال سرویس Safir برای سناریوهایی که از Bot ساده جدا هستند.',
    purpose:'Bale Safir یک اتصال جدا از Bale Bot است و ممکن است اطلاعات دسترسی متفاوتی مثل Access Key و Bot ID نیاز داشته باشد. از اطلاعات همان سرویس برای این Integration استفاده کنید.',
    steps:['اطلاعات دسترسی Safir را از پنل/سرویس مربوطه دریافت کنید.','در Integrations گزینه Bale Safir را انتخاب کنید.','فیلدهای Access Key، Bot ID یا آدرس سرویس را دقیقاً مطابق اطلاعات حساب وارد کنید.','اتصال را ذخیره و قبل از استفاده عملی یک تست انجام دهید.'],
    tips:['Credentialهای Bale Bot و Bale Safir را با هم جایگزین نکنید.','اگر سازمان چند حساب دارد، مشخص کنید هر اتصال متعلق به کدام حساب است.'],
    issues:['خطای authentication معمولاً از Access Key یا Bot ID نادرست است.','اگر اتصال ثبت می‌شود ولی ارسال انجام نمی‌شود، endpoint و دسترسی سرویس را بررسی کنید.'],
    actions:[{label:'تنظیم Bale Safir',href:sharedActions.integrations}],
   },
   {
    id:'instagram',title:'محدودیت‌های اینستاگرام',summary:'چرا اتصال اینستاگرام همیشه مساوی انتشار مستقیم همه نوع محتوا نیست.',
    purpose:'قابلیت‌های Instagram API به نوع حساب، اتصال Meta، permissionها و نوع محتوا وابسته است. اسماربیز باید این محدودیت را صریح نشان دهد و در صورت نبود Direct Publishing از مسیر Assisted استفاده کند.',
    steps:['در Integrations وضعیت اتصال Meta/Instagram و permissionهای موجود را بررسی کنید.','مطمئن شوید حساب مقصد همان حساب حرفه‌ای موردنظر است.','نوع محتوا را با قابلیت اتصال مقایسه کنید؛ Post، Reel و Story ممکن است شرایط متفاوت داشته باشند.','اگر انتشار مستقیم برای آن سناریو پشتیبانی نمی‌شود، از خروجی نهایی برای انتشار کمکی استفاده کنید.'],
    tips:['داشتن Instagram login به تنهایی تضمین Direct Publishing نیست.','محدودیت‌های Meta ممکن است در طول زمان تغییر کنند؛ متن خطای خود Integration را مبنا قرار دهید.'],
    issues:['اگر حساب یا Page صحیح نمایش داده نمی‌شود، ارتباط حساب حرفه‌ای و Meta را بررسی کنید.','اگر permission منقضی شده، اتصال را دوباره authorize کنید.'],
    actions:[{label:'بررسی اینستاگرام',href:sharedActions.integrations},{label:'محتوای آماده انتشار',href:sharedActions.studio}],
   },
   {
    id:'google-business',title:'پروفایل کسب‌وکار گوگل',summary:'اتصال حضور محلی برند و استفاده از قابلیت‌های مجاز Google Business.',
    purpose:'Google Business برای برندهای محلی می‌تواند بخشی از انتشار و اندازه‌گیری حضور محلی باشد. اتصال باید به حساب و Location صحیح مربوط باشد.',
    steps:['در Integrations اتصال Google Business را شروع کنید.','حساب گوگل صحیح و در صورت نمایش، Location درست کسب‌وکار را انتخاب کنید.','فقط قابلیت‌هایی را استفاده کنید که اتصال برای حساب شما فعال نشان می‌دهد.','بعد از انتشار یا همگام‌سازی، وضعیت نتیجه را در اسماربیز بررسی کنید.'],
    tips:['اگر چند شعبه دارید، Location اشتباه باعث انتشار در کسب‌وکار دیگری می‌شود.','نام، آدرس و اطلاعات حساس پروفایل را قبل از هر تغییر بررسی کنید.'],
    issues:['اگر Location دیده نمی‌شود، سطح دسترسی حساب گوگل را بررسی کنید.','اگر اتصال منقضی شده، دوباره احراز هویت کنید.'],
    actions:[{label:'اتصال Google Business',href:sharedActions.integrations},{label:'مشاهده Analytics',href:sharedActions.analytics}],
   },
   {
    id:'woocommerce',title:'ووکامرس',summary:'اتصال فروشگاه برای استفاده از اطلاعات واقعی محصول در عملیات محتوا.',
    purpose:'اتصال WooCommerce کمک می‌کند اطلاعات محصول از منبع واقعی فروشگاه بیاید و تیم مجبور نباشد قیمت، نام یا جزئیات محصول را دستی حدس بزند.',
    steps:['در WooCommerce دسترسی API مناسب برای اتصال موردنظر بسازید.','در Integrations آدرس فروشگاه و credentialهای خواسته‌شده را وارد کنید.','اتصال را تست کنید و مطمئن شوید فروشگاه صحیح شناسایی شده است.','در جریان محتوا از اطلاعات واقعی محصول استفاده کنید و قبل از انتشار، قیمت/موجودی حساس را دوباره بررسی کنید.'],
    tips:['کلیدهای API را عمومی نکنید.','برای اتصال فقط سطح دسترسی لازم را بدهید، نه بیشتر.','اطلاعاتی مثل قیمت و موجودی می‌تواند سریع تغییر کند.'],
    issues:['خطای 401/403 معمولاً از credential یا permission است.','اگر URL فروشگاه redirect یا firewall خاص دارد، دسترسی API را بررسی کنید.'],
    actions:[{label:'اتصال WooCommerce',href:sharedActions.integrations},{label:'پالس برند و محصولات',href:sharedActions.pulse}],
   },
   {
    id:'analytics',title:'تحلیل و UTM',summary:'اندازه‌گیری عملکرد محتوا و جلوگیری از تصمیم‌گیری بر اساس حدس.',
    purpose:'Analytics باید به شما نشان دهد چه چیزی منتشر شده، چه نتیجه‌ای داده و کدام کمپین یا CTA ارزش ادامه‌دادن دارد. UTM کمک می‌کند ترافیک قابل انتساب باشد.',
    steps:['Integration تحلیلی موردنیاز را متصل کنید.','برای لینک‌های کمپینی UTM منظم و قابل فهم بسازید.','نام campaign/source/medium را بین تیم ثابت نگه دارید.','بعد از انتشار اجازه دهید داده جمع شود و سپس آیتم‌ها یا کمپین‌ها را مقایسه کنید.','بین reach/engagement و conversion تفاوت قائل شوید و معیار را متناسب با هدف محتوا بخوانید.'],
    tips:['UTMهای تصادفی و نام‌گذاری متفاوت گزارش را خراب می‌کنند.','محتوای awareness را فقط با conversion مستقیم قضاوت نکنید.','برای نتیجه قابل اعتماد، بازه زمانی مشابه را مقایسه کنید.'],
    issues:['اگر Analytics خالی است، اول اتصال و سپس وجود داده واقعی در بازه انتخابی را بررسی کنید.','اگر همه ترافیک Direct دیده می‌شود، لینک‌ها و UTMها را بررسی کنید.'],
    actions:[{label:'باز کردن Analytics',href:sharedActions.analytics},{label:'مدیریت کمپین‌ها',href:sharedActions.campaigns},{label:'اتصال منبع داده',href:sharedActions.integrations}],
   },
   {
    id:'super-admin',title:'مدیریت کل',summary:'وظایف مدیریتی سطح بالا برای سلامت سیستم، کاربران و تنظیمات حساس.',
    purpose:'Super Admin برای عملیات عادی تولید محتوا نیست. این بخش برای مدیریت سطح سیستم، بررسی کاربران/سازمان‌ها و کارهای حساس مدیریتی است.',
    steps:['فقط با حساب دارای دسترسی مدیریتی وارد این بخش شوید.','قبل از تغییر تنظیمات سطح سیستم، اثر آن روی همه سازمان‌ها را بررسی کنید.','برای خطاهای عملیاتی ابتدا وضعیت سرویس و داده مرتبط را بررسی کنید، نه اینکه مستقیم داده کاربر را تغییر دهید.','تغییرات حساس را محدود، قابل ردیابی و با کمترین سطح دسترسی انجام دهید.'],
    tips:['دسترسی Super Admin را به کاربران عادی ندهید.','Credentialها و secretها نباید در رابط کاربری عمومی یا تیکت‌ها کپی شوند.'],
    issues:['اگر صفحه Admin را نمی‌بینید، احتمالاً نقش حساب شما اجازه آن را ندارد.','برای خطاهای tenant خاص، ابتدا همان سازمان/برند را شناسایی کنید تا داده سازمان دیگری تغییر نکند.'],
    actions:[{label:'باز کردن مدیریت کل',href:sharedActions.admin},{label:'تنظیمات',href:sharedActions.settings}],
   },
  ],
 },
 en:{
  title:'Help Center',subtitle:'Practical Smarbiz documentation: what each area does, how to use it, and what to check when something does not work.',search:'Search help…',noResults:'No help topic matches this search.',purpose:'What is this for?',steps:'How to do it',tips:'Important tips',issues:'If it does not work',actions:'Related actions',topicCount:'help topics',
  articles:[
   {id:'getting-started',title:'Getting started',summary:'The correct path from workspace setup to the first usable output.',purpose:'A good Smarbiz setup starts with brand context, then a real offer and publishing channels, and only then content generation. AI quality depends on the quality of this context.',steps:['Set the brand name, market, primary language and timezone.','Describe the business, audience, pains and desired outcomes clearly.','Add at least one real product or service with concrete benefits.','Define voice, content pillars and claims the system must avoid.','Choose only the channels you actually use, then move to Calendar or Content Studio.'],tips:['Specific facts are more useful than long promotional copy.','Keep data for different brands separated.','Primary language directly affects AI-generated output.'],issues:['If generation is unavailable, Brand Pulse or the main offer is usually incomplete.','If calendar times look wrong, check brand and profile timezones.'],actions:[{label:'Continue setup',href:sharedActions.onboarding},{label:'Complete Brand Pulse',href:sharedActions.pulse}]},
   {id:'brand-pulse',title:'Brand Pulse',summary:'The main source of truth for AI about the brand, audience, offer and constraints.',purpose:'Brand Pulse is the operational context Smarbiz uses when choosing angles, tone, CTAs and acceptable claims.',steps:['Write a clear business summary a new teammate can understand.','Enter the target audience, pains, questions and desired outcomes separately.','For each offer, add description, benefits, audience, objections and real proof points when available.','Complete voice, writing style, content pillars and preferred CTAs.','Add forbidden claims and sensitive rules, and keep them current when the business changes.'],tips:['Replace vague claims such as “high quality” with a concrete customer benefit.','Only add proof you can actually substantiate.','Write pains in the customer’s language, not internal company jargon.'],issues:['Generic output usually means the audience, pains or offer data is too thin.','If AI must never use a claim, add it explicitly to forbidden claims or Brand Rules.'],actions:[{label:'Open Brand Pulse',href:sharedActions.pulse},{label:'Build content calendar',href:sharedActions.calendar}]},
   {id:'calendar',title:'Content Calendar',summary:'AI weekly planning with angles, formats, goals, CTA and publishing time.',purpose:'The calendar should be more than a list of titles. Smarbiz uses Brand Pulse to create a balanced week across education, trust, engagement and conversion, with channel-native formats.',steps:['Complete Brand Pulse and at least one product/service first.','Choose the target week and, when relevant, a campaign.','Generate the week and review title, hook, brief, creative direction, goal and CTA for every item.','Edit or regenerate weak items without overwriting real approved or published work.','Move finalized items into Content Studio or approval.'],tips:['A strong week serves different funnel jobs instead of selling in every post.','Reels, Stories and Carousels need genuinely different execution concepts.','An active campaign should influence the week’s goals and offer.'],issues:['Generation errors often point to incomplete brand or offer data.','Existing real content should not be replaced by new AI output.','If ideas repeat, improve pains, objections, pillars and offer details.'],actions:[{label:'Open Calendar',href:sharedActions.calendar},{label:'Open Content Studio',href:sharedActions.studio}]},
   {id:'content-studio',title:'Content Studio',summary:'Turn a calendar idea into executable content ready for review.',purpose:'Content Studio is where a strategic idea becomes production-ready copy and creative direction that an approver can evaluate.',steps:['Start from a calendar item or a clearly defined topic.','Verify audience, channel, format and objective before final generation.','Review the output for facts, brand voice, risky claims and CTA.','Attach relevant assets when needed.','Send the finished version to approval before publishing.'],tips:['Keep content attached to the correct product/persona context.','Adapt length and structure to the actual channel.','Sensitive commercial, medical, legal or financial content still needs human review.'],issues:['If output feels off-brand, check product/persona links and Brand Pulse.','If an asset is missing, check the Assets area and upload status.'],actions:[{label:'Open Studio',href:sharedActions.studio},{label:'Assets',href:'/app/assets'}]},
   {id:'approvals',title:'Approval flow',summary:'Review content, record feedback and stop premature publishing.',purpose:'Approval separates “ready to review” from “allowed to publish,” especially for agencies and multi-person teams.',steps:['Move finished content into review.','Choose internal approval, public link, or a connected channel such as Telegram/Bale.','Ensure the approver can see the actual content and related assets.','Apply requested changes and resubmit when necessary.','Publish only after final approval.'],tips:['Public links are useful for clients without a Smarbiz account.','Material changes after approval should normally be approved again.','Keep Draft, Review, Approved and Published statuses distinct.'],issues:['If no approval message arrives, test the relevant integration.','If a public link fails, verify that it belongs to the correct item and is still valid.'],actions:[{label:'Open Approvals',href:sharedActions.approvals},{label:'Connect approval channel',href:sharedActions.integrations}]},
   {id:'publishing',title:'Direct vs assisted publishing',summary:'Understand when Smarbiz can publish through an API and when the final step remains manual.',purpose:'Not every platform or account type exposes direct publishing. Smarbiz separates Direct Publishing from Assisted Publishing so the workflow remains honest.',steps:['Check the Integration capability before assuming direct publishing is available.','For Direct Publishing, verify permissions and destination account and publish only approved content.','For Assisted Publishing, use the final copy/assets from Smarbiz and complete posting in the destination app.','Record the published state and, when possible, the final post URL.'],tips:['A connected integration does not automatically mean direct publishing is available.','API capability can vary by account type, permissions, platform policy or region.'],issues:['If there is no direct publish action, the connection may be approval/assisted only.','Expired permissions require re-authorization.'],actions:[{label:'Check Integrations',href:sharedActions.integrations},{label:'Approved content',href:sharedActions.approvals}]},
   {id:'telegram',title:'Telegram setup',summary:'Connect a bot for approvals and workflow messages.',purpose:'Telegram can carry approval requests and workflow notifications when a valid bot and destination are configured.',steps:['Create a bot with BotFather and obtain its token.','Open Telegram in Integrations and enter the required connection details.','Add the bot to the destination chat/group and grant needed send permissions.','Save and test the connection with a real approval or test message.'],tips:['Treat bot tokens like passwords.','For groups, confirm the bot is actually a member of the target group.'],issues:['Unauthorized usually means the token is invalid or revoked.','If the connection is healthy but no message arrives, verify the target chat/group and bot permissions.'],actions:[{label:'Connect Telegram',href:sharedActions.integrations},{label:'Test from Approvals',href:sharedActions.approvals}]},
   {id:'bale-bot',title:'Bale Bot setup',summary:'Connect Bale Bot for messages and approvals.',purpose:'Bale Bot can deliver workflow and approval messages to a Bale destination.',steps:['Create or obtain a valid Bale Bot token through the official Bale flow.','Open Bale in Integrations and enter the requested values.','Add the bot to the target conversation/group.','Save and run a test send.'],tips:['Protect the bot token as a credential.','Use clear connection names when several bots exist.'],issues:['Authentication failures usually mean token or bot access problems.','If delivery goes to the wrong destination, correct the conversation identifier/settings.'],actions:[{label:'Connect Bale',href:sharedActions.integrations},{label:'Open Approvals',href:sharedActions.approvals}]},
   {id:'bale-safir',title:'Bale Safir setup',summary:'Configure Safir separately from the standard Bale Bot integration.',purpose:'Bale Safir is a separate connection and may use different credentials such as an access key and bot ID.',steps:['Obtain Safir access details from the relevant service/account.','Choose Bale Safir in Integrations.','Enter the access key, bot ID and service address exactly as provided.','Save and test before relying on it in production.'],tips:['Do not swap Bale Bot and Bale Safir credentials.','Name connections clearly when an organization has several Bale accounts.'],issues:['Authentication errors usually point to the access key or bot ID.','If connection succeeds but delivery fails, verify the service endpoint and account permissions.'],actions:[{label:'Configure Bale Safir',href:sharedActions.integrations}]},
   {id:'instagram',title:'Instagram limitations',summary:'Why an Instagram connection does not always mean every format can be directly published.',purpose:'Instagram API capability depends on account type, Meta linkage, permissions and content format. Smarbiz should use assisted publishing when direct API publishing is unavailable.',steps:['Check Meta/Instagram connection status and available permissions.','Verify that the destination is the intended professional account.','Compare the content type with the capabilities shown by the integration.','Use assisted publishing when the exact scenario is not directly supported.'],tips:['Instagram login alone does not guarantee Direct Publishing.','Meta capabilities and policies can change; rely on the current integration status and error details.'],issues:['If the correct account/Page is missing, verify professional-account and Meta linkage.','Expired permissions require authorization again.'],actions:[{label:'Check Instagram',href:sharedActions.integrations},{label:'Open ready content',href:sharedActions.studio}]},
   {id:'google-business',title:'Google Business Profile',summary:'Connect the correct local business account/location.',purpose:'For local brands, Google Business can support local publishing and measurement where the connected account allows it.',steps:['Start Google Business connection in Integrations.','Choose the correct Google account and, when offered, the correct business location.','Use only capabilities that are shown as available for the account.','After publishing or syncing, verify the result in Smarbiz.'],tips:['With multiple branches, double-check the selected location.','Review sensitive profile details before changing them.'],issues:['If a location is missing, check the Google account’s access level.','Expired authorization requires reconnecting.'],actions:[{label:'Connect Google Business',href:sharedActions.integrations},{label:'View Analytics',href:sharedActions.analytics}]},
   {id:'woocommerce',title:'WooCommerce',summary:'Use real store/product data in content operations.',purpose:'WooCommerce integration reduces manual guessing around product details and allows workflows to use real store data.',steps:['Create the appropriate WooCommerce API access for the integration.','Enter the store URL and requested credentials in Integrations.','Test the connection and confirm the correct store is recognized.','Use actual product data in content and re-check fast-changing values such as price or stock before publishing.'],tips:['Never expose API keys publicly.','Grant only the access level required by the integration.','Price and inventory can change quickly.'],issues:['401/403 errors usually indicate credentials or permissions.','Redirects, firewalls or API restrictions on the store can block access.'],actions:[{label:'Connect WooCommerce',href:sharedActions.integrations},{label:'Brand Pulse & offers',href:sharedActions.pulse}]},
   {id:'analytics',title:'Analytics and UTM',summary:'Measure results instead of deciding from intuition alone.',purpose:'Analytics links published work to outcomes. Consistent UTM naming helps attribute traffic to the correct content and campaign.',steps:['Connect the required analytics source.','Use consistent UTM parameters on campaign links.','Standardize campaign/source/medium naming across the team.','Allow data to accumulate before comparing items or campaigns.','Read awareness, engagement and conversion metrics according to the content goal.'],tips:['Inconsistent UTM naming ruins attribution.','Do not judge awareness content only by direct conversions.','Compare similar time windows for more reliable conclusions.'],issues:['If Analytics is empty, first check the connection, then whether real data exists in the selected period.','If traffic appears mostly Direct, inspect campaign links and UTMs.'],actions:[{label:'Open Analytics',href:sharedActions.analytics},{label:'Campaigns',href:sharedActions.campaigns},{label:'Connect data source',href:sharedActions.integrations}]},
   {id:'super-admin',title:'Super Admin',summary:'High-level system administration for users, organizations and sensitive settings.',purpose:'Super Admin is not part of the normal content workflow. It exists for system-level administration and sensitive operational tasks.',steps:['Use this area only with an authorized admin account.','Consider the impact on all organizations before changing system-level settings.','For operational errors, inspect service/data state before changing user data directly.','Keep sensitive changes minimal, traceable and least-privilege.'],tips:['Do not grant Super Admin to normal users.','Never paste secrets into public UI, screenshots or tickets.'],issues:['If Admin is not visible, the account likely lacks the required role.','For tenant-specific issues, identify the exact organization/brand before making changes.'],actions:[{label:'Open Super Admin',href:sharedActions.admin},{label:'Settings',href:sharedActions.settings}]},
  ],
 },
 de:{
  title:'Hilfe-Center',subtitle:'Praktische Smarbiz-Dokumentation: Was jeder Bereich macht, wie Sie ihn verwenden und was Sie bei Problemen prüfen sollten.',search:'Hilfe durchsuchen…',noResults:'Kein Hilfethema passt zu dieser Suche.',purpose:'Wofür ist dieser Bereich?',steps:'So gehen Sie vor',tips:'Wichtige Hinweise',issues:'Wenn es nicht funktioniert',actions:'Zugehörige Aktionen',topicCount:'Hilfethemen',
  articles:[
   {id:'getting-started',title:'Erste Schritte',summary:'Der richtige Weg vom Workspace-Setup bis zum ersten nutzbaren Ergebnis.',purpose:'Ein gutes Smarbiz-Setup beginnt mit dem Markenkontext, danach folgen ein echtes Angebot und die verwendeten Kanäle. Erst dann sollte Content generiert werden. Die Qualität der KI hängt direkt von diesem Kontext ab.',steps:['Markenname, Markt, Hauptsprache und Zeitzone festlegen.','Unternehmen, Zielgruppe, Probleme und gewünschte Ergebnisse klar beschreiben.','Mindestens ein echtes Produkt oder eine Dienstleistung mit konkreten Vorteilen hinzufügen.','Ton, Content-Säulen und Aussagen definieren, die vermieden werden müssen.','Nur tatsächlich genutzte Kanäle auswählen und danach Kalender oder Content Studio öffnen.'],tips:['Konkrete Fakten sind nützlicher als lange Werbetexte.','Daten verschiedener Marken getrennt halten.','Die Hauptsprache beeinflusst die KI-Ausgabe direkt.'],issues:['Wenn Generierung nicht verfügbar ist, fehlen meist Brand-Pulse- oder Angebotsdaten.','Bei falschen Kalenderzeiten die Zeitzonen von Marke und Profil prüfen.'],actions:[{label:'Setup fortsetzen',href:sharedActions.onboarding},{label:'Brand Pulse vervollständigen',href:sharedActions.pulse}]},
   {id:'brand-pulse',title:'Brand Pulse',summary:'Die zentrale Wissensbasis der KI für Marke, Zielgruppe, Angebot und Regeln.',purpose:'Brand Pulse ist der operative Kontext, den Smarbiz für Themenwinkel, Tonalität, CTAs und zulässige Aussagen verwendet.',steps:['Eine klare Unternehmensbeschreibung schreiben.','Zielgruppe, Probleme, Fragen und gewünschte Ergebnisse getrennt eintragen.','Für jedes Angebot Beschreibung, Vorteile, Zielgruppe, Einwände und belegbare Nachweise ergänzen.','Tonalität, Schreibstil, Content-Säulen und bevorzugte CTAs vervollständigen.','Verbotene Aussagen und sensible Regeln eintragen und aktuell halten.'],tips:['Vage Aussagen wie „höchste Qualität“ durch konkrete Kundenvorteile ersetzen.','Nur Nachweise eintragen, die tatsächlich belegt werden können.','Probleme in der Sprache der Kunden formulieren.'],issues:['Generische Ergebnisse bedeuten meist, dass Zielgruppen- oder Angebotsdaten zu dünn sind.','Nicht erlaubte Aussagen ausdrücklich in Forbidden Claims oder Brand Rules eintragen.'],actions:[{label:'Brand Pulse öffnen',href:sharedActions.pulse},{label:'Content-Kalender erstellen',href:sharedActions.calendar}]},
   {id:'calendar',title:'Content-Kalender',summary:'KI-Wochenplanung mit Themenwinkel, Format, Ziel, CTA und Veröffentlichungszeit.',purpose:'Der Kalender soll mehr als Überschriften liefern. Smarbiz erstellt auf Basis des Brand Pulse eine ausgewogene Woche aus Education, Vertrauen, Interaktion und Conversion.',steps:['Brand Pulse und mindestens ein Produkt/eine Dienstleistung vervollständigen.','Zielwoche und bei Bedarf eine Kampagne auswählen.','Woche generieren und Titel, Hook, Briefing, Creative Direction, Ziel und CTA prüfen.','Schwache Einträge bearbeiten oder neu generieren, ohne echte freigegebene/veröffentlichte Inhalte zu überschreiben.','Finale Einträge ins Content Studio oder in die Freigabe geben.'],tips:['Eine gute Woche erfüllt mehrere Funnel-Aufgaben und verkauft nicht in jedem Beitrag direkt.','Reels, Stories und Carousels brauchen unterschiedliche Ausführungen.','Eine aktive Kampagne sollte Ziele und Angebot der Woche beeinflussen.'],issues:['Generierungsfehler weisen häufig auf fehlende Marken- oder Angebotsdaten hin.','Bestehende echte Inhalte dürfen nicht durch neue KI-Ausgaben ersetzt werden.','Bei Wiederholungen Zielgruppenprobleme, Einwände und Content-Säulen präzisieren.'],actions:[{label:'Kalender öffnen',href:sharedActions.calendar},{label:'Content Studio öffnen',href:sharedActions.studio}]},
   {id:'content-studio',title:'Content Studio',summary:'Aus einer Idee umsetzbaren Content für die Freigabe machen.',purpose:'Im Content Studio wird aus einer strategischen Idee ein ausführbarer Text samt Creative Direction, den ein Freigeber konkret prüfen kann.',steps:['Mit einem Kalendereintrag oder klar definierten Thema starten.','Zielgruppe, Kanal, Format und Ziel vor der finalen Generierung prüfen.','Ausgabe auf Fakten, Markenton, riskante Claims und CTA prüfen.','Bei Bedarf passende Assets hinzufügen.','Fertige Version vor der Veröffentlichung zur Freigabe senden.'],tips:['Content mit dem richtigen Produkt-/Persona-Kontext verbunden halten.','Länge und Struktur an den echten Kanal anpassen.','Sensible kommerzielle, medizinische, rechtliche oder finanzielle Inhalte weiterhin menschlich prüfen.'],issues:['Bei unpassendem Markenton Produkt-/Persona-Verknüpfung und Brand Pulse prüfen.','Bei fehlenden Dateien Assets und Upload-Status prüfen.'],actions:[{label:'Studio öffnen',href:sharedActions.studio},{label:'Assets',href:'/app/assets'}]},
   {id:'approvals',title:'Freigabeprozess',summary:'Content prüfen, Feedback erfassen und zu frühe Veröffentlichung verhindern.',purpose:'Freigaben trennen „bereit zur Prüfung“ von „darf veröffentlicht werden“ und sind besonders für Agenturen und Teams wichtig.',steps:['Fertigen Content in den Review-Status bringen.','Interne Freigabe, öffentlichen Link oder verbundenen Kanal wie Telegram/Bale wählen.','Sicherstellen, dass der Freigeber Inhalt und relevante Assets sehen kann.','Änderungswünsche umsetzen und falls nötig erneut senden.','Erst nach finaler Freigabe veröffentlichen.'],tips:['Öffentliche Links eignen sich für Kunden ohne Smarbiz-Konto.','Wesentliche Änderungen nach Freigabe sollten erneut freigegeben werden.','Draft, Review, Approved und Published klar getrennt halten.'],issues:['Wenn keine Freigabenachricht ankommt, die entsprechende Integration testen.','Bei defektem öffentlichen Link prüfen, ob er zum richtigen Eintrag gehört und noch gültig ist.'],actions:[{label:'Freigaben öffnen',href:sharedActions.approvals},{label:'Freigabekanal verbinden',href:sharedActions.integrations}]},
   {id:'publishing',title:'Direkte und assistierte Veröffentlichung',summary:'Wann Smarbiz per API veröffentlichen kann und wann der letzte Schritt manuell bleibt.',purpose:'Nicht jede Plattform oder jeder Kontotyp erlaubt Direct Publishing. Smarbiz trennt direkte und assistierte Veröffentlichung, damit der Workflow transparent bleibt.',steps:['In Integrations prüfen, welche Publishing-Fähigkeit die Verbindung wirklich hat.','Bei Direct Publishing Berechtigungen und Zielkonto prüfen und nur freigegebenen Content veröffentlichen.','Bei Assisted Publishing finale Texte/Assets aus Smarbiz nehmen und im Zielsystem posten.','Veröffentlichungsstatus und wenn möglich die finale Post-URL in Smarbiz erfassen.'],tips:['Eine verbundene Integration bedeutet nicht automatisch Direct Publishing.','API-Funktionen können von Kontotyp, Berechtigungen, Plattformregeln oder Region abhängen.'],issues:['Fehlt die direkte Veröffentlichungsaktion, ist die Verbindung möglicherweise nur für Approval/Assisted gedacht.','Abgelaufene Berechtigungen erfordern erneute Autorisierung.'],actions:[{label:'Integrationen prüfen',href:sharedActions.integrations},{label:'Freigegebener Content',href:sharedActions.approvals}]},
   {id:'telegram',title:'Telegram einrichten',summary:'Bot für Freigaben und Workflow-Nachrichten verbinden.',purpose:'Telegram kann Freigabeanfragen und Workflow-Nachrichten senden, wenn ein gültiger Bot und das richtige Ziel konfiguriert sind.',steps:['Mit BotFather einen Bot erstellen und Token erhalten.','Telegram in Integrations öffnen und die geforderten Daten eintragen.','Bot zum Ziel-Chat/zur Gruppe hinzufügen und nötige Senderechte vergeben.','Verbindung speichern und mit einer echten Freigabe oder Testnachricht prüfen.'],tips:['Bot-Token wie Passwörter behandeln.','Bei Gruppen sicherstellen, dass der Bot wirklich Mitglied der Zielgruppe ist.'],issues:['Unauthorized bedeutet meist ungültigen oder widerrufenen Token.','Wenn Verbindung gesund ist, aber nichts ankommt, Ziel-Chat und Bot-Rechte prüfen.'],actions:[{label:'Telegram verbinden',href:sharedActions.integrations},{label:'Über Freigaben testen',href:sharedActions.approvals}]},
   {id:'bale-bot',title:'Bale Bot einrichten',summary:'Bale Bot für Nachrichten und Freigaben verbinden.',purpose:'Bale Bot kann Workflow- und Freigabenachrichten an ein Bale-Ziel senden.',steps:['Einen gültigen Bale-Bot-Token über den offiziellen Bale-Prozess beziehen.','Bale in Integrations öffnen und die geforderten Werte eintragen.','Bot zur Ziel-Unterhaltung oder Gruppe hinzufügen.','Speichern und Testversand durchführen.'],tips:['Bot-Token als Zugangsdaten schützen.','Bei mehreren Bots eindeutige Verbindungsnamen verwenden.'],issues:['Authentifizierungsfehler weisen meist auf Token oder Bot-Zugriff hin.','Bei falschem Ziel die Conversation-ID bzw. Zielkonfiguration korrigieren.'],actions:[{label:'Bale verbinden',href:sharedActions.integrations},{label:'Freigaben öffnen',href:sharedActions.approvals}]},
   {id:'bale-safir',title:'Bale Safir einrichten',summary:'Safir getrennt von der normalen Bale-Bot-Verbindung konfigurieren.',purpose:'Bale Safir ist eine separate Verbindung und kann andere Zugangsdaten wie Access Key und Bot ID verwenden.',steps:['Safir-Zugangsdaten vom zuständigen Dienst/Konto beziehen.','Bale Safir in Integrations auswählen.','Access Key, Bot ID und Service-Adresse exakt eintragen.','Speichern und vor Produktiveinsatz testen.'],tips:['Bale-Bot- und Bale-Safir-Zugangsdaten nicht vertauschen.','Bei mehreren Bale-Konten Verbindungen eindeutig benennen.'],issues:['Authentifizierungsfehler betreffen meist Access Key oder Bot ID.','Wenn Verbindung steht, aber keine Zustellung erfolgt, Endpoint und Kontorechte prüfen.'],actions:[{label:'Bale Safir konfigurieren',href:sharedActions.integrations}]},
   {id:'instagram',title:'Instagram-Einschränkungen',summary:'Warum eine Instagram-Verbindung nicht jedes Format automatisch direkt veröffentlichen kann.',purpose:'Instagram-API-Funktionen hängen von Kontotyp, Meta-Verknüpfung, Berechtigungen und Content-Format ab. Ohne Direct Publishing sollte Smarbiz Assisted Publishing verwenden.',steps:['Meta-/Instagram-Verbindungsstatus und Berechtigungen prüfen.','Sicherstellen, dass das richtige professionelle Zielkonto gewählt ist.','Content-Typ mit den von der Integration angezeigten Fähigkeiten vergleichen.','Assisted Publishing verwenden, wenn der konkrete Fall nicht direkt unterstützt wird.'],tips:['Ein Instagram-Login allein garantiert kein Direct Publishing.','Meta-Funktionen und Regeln können sich ändern; aktuellen Integrationsstatus und Fehlermeldung beachten.'],issues:['Fehlt das richtige Konto/die Page, Verknüpfung zwischen professionellem Konto und Meta prüfen.','Abgelaufene Berechtigungen erneut autorisieren.'],actions:[{label:'Instagram prüfen',href:sharedActions.integrations},{label:'Fertigen Content öffnen',href:sharedActions.studio}]},
   {id:'google-business',title:'Google Unternehmensprofil',summary:'Das richtige lokale Unternehmenskonto bzw. den richtigen Standort verbinden.',purpose:'Für lokale Marken kann Google Business lokale Veröffentlichung und Messung unterstützen, sofern das verbundene Konto die Funktion erlaubt.',steps:['Google Business in Integrations verbinden.','Richtiges Google-Konto und gegebenenfalls richtigen Unternehmensstandort auswählen.','Nur Funktionen verwenden, die für das Konto als verfügbar angezeigt werden.','Nach Veröffentlichung/Synchronisierung das Ergebnis in Smarbiz prüfen.'],tips:['Bei mehreren Filialen den Standort besonders sorgfältig prüfen.','Sensible Profildaten vor Änderungen kontrollieren.'],issues:['Fehlt ein Standort, Zugriffsrechte des Google-Kontos prüfen.','Abgelaufene Autorisierung erneut verbinden.'],actions:[{label:'Google Business verbinden',href:sharedActions.integrations},{label:'Analytics öffnen',href:sharedActions.analytics}]},
   {id:'woocommerce',title:'WooCommerce',summary:'Echte Shop- und Produktdaten in Content-Workflows verwenden.',purpose:'Die WooCommerce-Integration reduziert manuelle Fehler bei Produktdaten und ermöglicht die Nutzung echter Shop-Informationen.',steps:['Geeigneten WooCommerce-API-Zugang erstellen.','Shop-URL und geforderte Zugangsdaten in Integrations eintragen.','Verbindung testen und richtigen Shop bestätigen.','Echte Produktdaten nutzen und schnell veränderliche Werte wie Preis/Bestand vor Veröffentlichung erneut prüfen.'],tips:['API-Schlüssel niemals öffentlich teilen.','Nur die erforderlichen Berechtigungen vergeben.','Preis und Bestand können sich schnell ändern.'],issues:['401/403 bedeutet meist Zugangsdaten oder Berechtigungen.','Redirects, Firewalls oder API-Sperren im Shop können den Zugriff blockieren.'],actions:[{label:'WooCommerce verbinden',href:sharedActions.integrations},{label:'Brand Pulse & Angebote',href:sharedActions.pulse}]},
   {id:'analytics',title:'Analytics und UTM',summary:'Ergebnisse messen statt nur nach Gefühl zu entscheiden.',purpose:'Analytics verbindet veröffentlichten Content mit Ergebnissen. Einheitliche UTM-Namen machen Traffic einer Kampagne oder einem Inhalt zuordenbar.',steps:['Benötigte Analytics-Quelle verbinden.','Für Kampagnenlinks einheitliche UTM-Parameter verwenden.','Campaign/Source/Medium im Team standardisieren.','Daten sammeln lassen, bevor Inhalte oder Kampagnen verglichen werden.','Awareness-, Engagement- und Conversion-Kennzahlen passend zum Content-Ziel lesen.'],tips:['Uneinheitliche UTM-Namen zerstören Attribution.','Awareness-Content nicht nur an direkten Conversions messen.','Vergleichbare Zeiträume verwenden.'],issues:['Bei leeren Analytics zuerst Verbindung und dann vorhandene Echtdaten im Zeitraum prüfen.','Wenn fast alles als Direct erscheint, Kampagnenlinks und UTMs prüfen.'],actions:[{label:'Analytics öffnen',href:sharedActions.analytics},{label:'Kampagnen',href:sharedActions.campaigns},{label:'Datenquelle verbinden',href:sharedActions.integrations}]},
   {id:'super-admin',title:'Super Admin',summary:'Systemweite Administration für Benutzer, Organisationen und sensible Einstellungen.',purpose:'Super Admin gehört nicht zum normalen Content-Workflow. Der Bereich ist für systemweite und sensible Administrationsaufgaben gedacht.',steps:['Nur mit autorisiertem Admin-Konto verwenden.','Vor systemweiten Änderungen Auswirkungen auf alle Organisationen prüfen.','Bei Betriebsfehlern zuerst Service- und Datenstatus untersuchen, bevor Nutzerdaten geändert werden.','Sensible Änderungen minimal, nachvollziehbar und mit Least-Privilege durchführen.'],tips:['Super-Admin-Rechte nicht an normale Nutzer vergeben.','Secrets niemals in öffentliche UI, Screenshots oder Tickets kopieren.'],issues:['Wenn Admin nicht sichtbar ist, fehlt dem Konto wahrscheinlich die nötige Rolle.','Bei tenant-spezifischen Problemen die genaue Organisation/Marke vor Änderungen identifizieren.'],actions:[{label:'Super Admin öffnen',href:sharedActions.admin},{label:'Einstellungen',href:sharedActions.settings}]},
  ],
 },
};

export default function Page({params}:{params:Promise<{locale:string}>}){
 const {locale}=use(params);
 return <AppShell locale={locale}><Help locale={locale}/></AppShell>;
}

function localHref(locale:string,href:string){
 return `/${locale}${href}`;
}

function Help({locale}:{locale:string}){
 const c=copy[locale]||copy.en;
 const [selectedId,setSelectedId]=useState(c.articles[0].id);
 const [query,setQuery]=useState('');
 const normalized=query.trim().toLocaleLowerCase();
 const filtered=useMemo(()=>{
  if(!normalized)return c.articles;
  return c.articles.filter(article=>[
   article.title,article.summary,article.purpose,...article.steps,...article.tips,...article.issues,
  ].join(' ').toLocaleLowerCase().includes(normalized));
 },[c.articles,normalized]);
 const selected=useMemo(()=>c.articles.find(article=>article.id===selectedId)||filtered[0]||c.articles[0],[c.articles,filtered,selectedId]);

 return <div className="space-y-6">
  <section className="panel overflow-hidden p-6 md:p-8">
   <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
    <div className="max-w-3xl">
     <span className="badge">Smarbiz Docs</span>
     <h1 className="mt-3 text-3xl font-black md:text-4xl">{c.title}</h1>
     <p className="muted mt-3 leading-7">{c.subtitle}</p>
    </div>
    <div className="min-w-64 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm">
     <b className="text-2xl font-black text-slate-900">{c.articles.length}</b>
     <span className="muted ms-2">{c.topicCount}</span>
    </div>
   </div>
   <label className="mt-6 block">
    <span className="sr-only">{c.search}</span>
    <input className="field" value={query} onChange={event=>setQuery(event.target.value)} placeholder={c.search}/>
   </label>
  </section>

  <div className="grid gap-6 lg:grid-cols-[19rem_minmax(0,1fr)]">
   <aside className="panel h-fit p-3 lg:sticky lg:top-5">
    {filtered.length?filtered.map(article=><button
     type="button"
     className={`block w-full rounded-xl p-3 text-start transition ${article.id===selected.id?'bg-blue-50 text-blue-900':'hover:bg-slate-50'}`}
     onClick={()=>setSelectedId(article.id)}
     key={article.id}
    >
     <b className="block text-sm">{article.title}</b>
     <span className="muted mt-1 block text-xs leading-5">{article.summary}</span>
    </button>):<p className="muted p-4 text-sm">{c.noResults}</p>}
   </aside>

   <article className="panel overflow-hidden">
    <header className="border-b border-slate-100 p-6 md:p-8">
     <span className="badge">{selected.title}</span>
     <h2 className="mt-4 text-3xl font-black md:text-4xl">{selected.title}</h2>
     <p className="muted mt-3 max-w-3xl text-base leading-7">{selected.summary}</p>
    </header>

    <div className="grid gap-8 p-6 md:p-8 xl:grid-cols-[minmax(0,1fr)_18rem]">
     <div className="space-y-8">
      <GuideSection title={c.purpose}><p className="leading-7 text-slate-700">{selected.purpose}</p></GuideSection>
      <GuideSection title={c.steps}>
       <ol className="space-y-4">
        {selected.steps.map((step,index)=><li className="flex gap-3" key={step}>
         <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-indigo-50 text-xs font-black text-indigo-700">{index+1}</span>
         <span className="pt-0.5 leading-6 text-slate-700">{step}</span>
        </li>)}
       </ol>
      </GuideSection>
      <div className="grid gap-4 md:grid-cols-2">
       <InfoCard title={c.tips} items={selected.tips}/>
       <InfoCard title={c.issues} items={selected.issues}/>
      </div>
     </div>

     <aside className="h-fit rounded-2xl border border-slate-200 bg-slate-50 p-5 xl:sticky xl:top-5">
      <h3 className="font-black">{c.actions}</h3>
      <div className="mt-4 flex flex-col gap-2">
       {selected.actions.map(action=><Link className="chip justify-center" href={localHref(locale,action.href)} key={`${selected.id}-${action.href}`}>{action.label}</Link>)}
      </div>
     </aside>
    </div>
   </article>
  </div>
 </div>;
}

function GuideSection({title,children}:{title:string;children:React.ReactNode}){
 return <section><h3 className="mb-4 text-lg font-black text-slate-900">{title}</h3>{children}</section>;
}

function InfoCard({title,items}:{title:string;items:string[]}){
 return <section className="rounded-2xl border border-slate-200 bg-white p-5">
  <h3 className="font-black">{title}</h3>
  <ul className="mt-4 space-y-3">
   {items.map(item=><li className="flex gap-2 text-sm leading-6 text-slate-700" key={item}><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400"/>{item}</li>)}
  </ul>
 </section>;
}
