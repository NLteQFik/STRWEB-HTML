import random
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from hotel.models import (
    Article,
    Banner,
    Booking,
    Client,
    CompanyInfo,
    Employee,
    ExtraService,
    Glossary,
    Partner,
    Payment,
    PromoCode,
    Review,
    Room,
    RoomCategory,
    Vacancy,
)


TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(text):
    return "".join(TRANSLIT_MAP.get(c, c) for c in text.lower())


class Command(BaseCommand):
    help = "Полностью очищает и заполняет базу тестовыми данными гостиницы."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        self.stdout.write("Очистка базы данных...")
        self._clear_db()
        self.stdout.write(self.style.SUCCESS("База очищена."))

        self.stdout.write("Создание справочников и контента...")
        categories = self._create_categories()
        services = self._create_extra_services()
        rooms = self._create_rooms(categories)
        employees = self._create_employees()
        clients = self._create_clients()

        self._create_bookings_and_payments(rooms=rooms, clients=clients, services=services)
        self._create_articles()
        self._create_banners()
        self._create_partners()
        self._create_company_info()
        self._create_glossary()
        self._create_vacancies()
        self._create_reviews()
        self._create_promocodes()

        self.stdout.write(self.style.SUCCESS("База успешно заполнена тестовыми данными."))
        self.stdout.write(
            f"Сотрудников: {len(employees)} | "
            f"Номеров: {len(rooms)} | "
            f"Клиентов: {len(clients)} | "
            "Новости: 3 | FAQ: 5 | "
            "Вакансии: 10 | Отзывы: 10 | Промокоды: 10"
        )

    def _clear_db(self) -> None:
        Payment.objects.all().delete()
        Booking.objects.all().delete()
        Room.objects.all().delete()
        RoomCategory.objects.all().delete()
        ExtraService.objects.all().delete()
        Employee.objects.all().delete()
        Client.objects.all().delete()
        Article.objects.all().delete()
        CompanyInfo.objects.all().delete()
        Glossary.objects.all().delete()
        Vacancy.objects.all().delete()
        Review.objects.all().delete()
        PromoCode.objects.all().delete()
        Banner.objects.all().delete()
        Partner.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_categories(self):
        return [
            RoomCategory.objects.create(
                name="Люкс",
                capacity=4,
                description=(
                    "Просторный номер повышенной комфортности с отдельной зоной отдыха, "
                    "рабочим пространством и расширенным набором сервисов."
                ),
                base_price=Decimal("420.00"),
            ),
            RoomCategory.objects.create(
                name="Полулюкс",
                capacity=3,
                description=(
                    "Уютный номер с улучшенной мебелью и видом на город, "
                    "подходит для семейного размещения и деловых поездок."
                ),
                base_price=Decimal("280.00"),
            ),
            RoomCategory.objects.create(
                name="Стандарт",
                capacity=2,
                description=(
                    "Функциональный номер со всем необходимым для комфортного проживания "
                    "одного или двух гостей."
                ),
                base_price=Decimal("160.00"),
            ),
        ]

    def _create_extra_services(self):
        data = [
            ("Завтрак", Decimal("20.00")),
            ("Трансфер", Decimal("35.00")),
            ("SPA", Decimal("55.00")),
            ("Поздний выезд", Decimal("25.00")),
        ]
        return [ExtraService.objects.create(name=name, price=price) for name, price in data]

    def _create_rooms(self, categories):
        rooms = []
        category_map = {category.name: category for category in categories}
        room_plan = [
            ("101", Room.RoomStatus.FREE, "Стандарт"),
            ("102", Room.RoomStatus.OCCUPIED, "Стандарт"),
            ("103", Room.RoomStatus.CLEANING, "Стандарт"),
            ("201", Room.RoomStatus.FREE, "Полулюкс"),
            ("202", Room.RoomStatus.OCCUPIED, "Полулюкс"),
            ("203", Room.RoomStatus.FREE, "Полулюкс"),
            ("301", Room.RoomStatus.FREE, "Люкс"),
            ("302", Room.RoomStatus.OCCUPIED, "Люкс"),
            ("303", Room.RoomStatus.CLEANING, "Люкс"),
            ("304", Room.RoomStatus.FREE, "Люкс"),
        ]
        for idx, (room_number, status, category_name) in enumerate(room_plan, start=1):
            rooms.append(
                Room.objects.create(
                    room_number=room_number,
                    status=status,
                    category=category_map[category_name],
                    photo=None,
                )
            )
        return rooms

    def _create_employees(self):
        emp_first_m = ["Алексей", "Дмитрий", "Сергей", "Андрей", "Максим"]
        emp_first_f = ["Мария", "Елена", "Ольга", "Анна", "Татьяна"]
        emp_last_m = ["Иванов", "Петров", "Сидоров", "Козлов", "Смирнов", "Климов", "Белов", "Зайцев", "Новиков", "Громов"]
        emp_patr_m = ["Сергеевич", "Алексеевич", "Иванович", "Николаевич", "Петрович"]
        emp_patr_f = ["Сергеевна", "Алексеевна", "Ивановна", "Николаевна", "Петровна"]
        positions = [
            "Администратор ресепшн", "Старший администратор", "Менеджер по бронированию",
            "Консьерж", "Менеджер по работе с гостями", "Техник по эксплуатации",
            "Руководитель housekeeping", "Горничная", "Повар завтраков", "Маркетолог",
        ]
        codes = ["29", "33", "44", "25"]
        employees = []
        used_names = set()
        for index in range(1, 11):
            while True:
                is_female = random.choice([True, False])
                fn = random.choice(emp_first_f if is_female else emp_first_m)
                ln = random.choice(emp_last_m)
                if is_female:
                    ln = ln.rstrip("в") + "ва" if ln.endswith("в") else ln + "ва"
                pt = random.choice(emp_patr_f if is_female else emp_patr_m)
                full_name = f"{ln} {fn} {pt}"
                if full_name not in used_names:
                    used_names.add(full_name)
                    break
            position = positions[index - 1]
            phone = f"+375 ({random.choice(codes)}) {random.randint(100,999):03d}-{random.randint(10,99):02d}-{random.randint(10,99):02d}"
            username = f"employee{index}"
            email_local = transliterate(ln)
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{email_local}@gmail.com"}
            )
            if user_created:
                user.set_password("employee12345")
                user.save()

            employee, _ = Employee.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'last_name': ln,
                    'first_name': fn,
                    'patronymic': pt,
                    'position': position,
                    'phone': phone,
                    'birth_date': date(1985, 1, 1) + timedelta(days=random.randint(200, 500)),
                    'photo': None,
                    'work_description': (
                        f"{full_name} отвечает за направление '{position}', "
                        "координирует процессы и поддерживает стандарты сервиса."
                    ),
                    'timezone': 'Europe/Minsk',
                }
            )
            employees.append(employee)
        return employees

    def _create_clients(self):
        Client.objects.filter(user__username__startswith="employee").delete()
        cl_first_m = ["Андрей", "Максим", "Виктор", "Сергей", "Илья", "Денис", "Павел", "Артём", "Владимир", "Никита"]
        cl_first_f = ["Алина", "Наталья", "Екатерина", "Анна", "Ирина", "Светлана", "Ольга", "Юлия", "Дарья", "Ксения"]
        cl_last_m = ["Кравченко", "Лебедев", "Шевченко", "Королев", "Орлов", "Морозов", "Волков", "Соколов", "Кузнецов", "Попов"]
        cl_patr_m = ["Петрович", "Ильич", "Павлович", "Романович", "Денисович", "Олегович", "Игоревич", "Владимирович", "Алексеевич", "Сергеевич"]
        cl_patr_f = ["Петровна", "Ильинична", "Павловна", "Романовна", "Денисовна", "Олеговна", "Игоревна", "Владимировна", "Алексеевна", "Сергеевна"]
        codes = ["29", "33", "44", "25"]
        comment_pool = [
            "", "", "",
            "Постоянный клиент, предпочитает люкс.",
            "Просит номер с видом на город.",
            "Важна детская кроватка и питание.",
            "Требуется рабочее место в номере.",
            "Предпочитает тихие номера вдали от лифта.",
            "Нужны дополнительные полотенца.",
            "Бизнес-гость, важен стабильный Wi-Fi.",
            "Семейный тур выходного дня.",
            "Приезжает на конференцию, важен поздний выезд.",
        ]
        clients = []
        used_names = set()
        for index in range(1, 11):
            while True:
                is_female = random.choice([True, False])
                fn = random.choice(cl_first_f if is_female else cl_first_m)
                ln = random.choice(cl_last_m)
                if is_female:
                    ln = ln.rstrip("в") + "ва" if ln.endswith("в") else ln + "ва"
                pt = random.choice(cl_patr_f if is_female else cl_patr_m)
                full_name = f"{ln} {fn} {pt}"
                if full_name not in used_names:
                    used_names.add(full_name)
                    break
            phone = f"+375 ({random.choice(codes)}) {random.randint(100,999):03d}-{random.randint(10,99):02d}-{random.randint(10,99):02d}"
            children_count = random.randint(0, 5)
            comment = random.choice(comment_pool)
            username = f"client{index}"
            email_local = transliterate(ln)
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{email_local}@gmail.com"}
            )
            if user_created:
                user.set_password("client12345")
                user.save()

            client, _ = Client.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'last_name': ln,
                    'first_name': fn,
                    'patronymic': pt,
                    'phone': phone,
                    'birth_date': date(1980, 1, 1) + timedelta(days=random.randint(3000, 7000)),
                    'children_count': children_count,
                    'timezone': 'Europe/Minsk',
                    'comment': comment,
                }
            )
            clients.append(client)
        return clients

    def _random_dt_before_deadline(self, deadline_date, max_days_before=60):
        days_before = random.randint(1, max_days_before)
        hour = random.randint(8, 22)
        minute = random.randint(0, 59)
        return datetime(
            deadline_date.year, deadline_date.month, deadline_date.day,
            hour, minute, tzinfo=dt_timezone.utc,
        ) - timedelta(days=days_before)

    def _create_bookings_and_payments(self, rooms, clients, services):
        deadline = date(2026, 5, 17)
        for index, client in enumerate(clients):
            room = rooms[index]
            check_in = date(2026, 4, 1) + timedelta(days=random.randint(0, 121))
            stay = random.randint(1, 7)
            check_out = min(check_in + timedelta(days=stay), date(2026, 7, 31))
            total_cost = Decimal(str(random.randint(80, 200) * stay * random.choice([16, 28, 42]))) / Decimal("10")
            status = random.choices(
                [Booking.BookingStatus.ACTIVE, Booking.BookingStatus.FINISHED, Booking.BookingStatus.CANCELED],
                weights=[3, 6, 1],
            )[0]
            created_at = self._random_dt_before_deadline(deadline, max_days_before=60)
            updated_offset = timedelta(
                days=random.randint(0, 5), hours=random.randint(0, 12)
            )
            updated_at = min(created_at + updated_offset, created_at + timedelta(days=10))
            booking = Booking.objects.create(
                room=room,
                client=client,
                check_in_date=check_in,
                check_out_date=check_out,
                total_cost=total_cost,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
            )
            booking.extra_services.set(random.sample(list(services), random.randint(0, len(services))))

            paid_at = self._random_dt_before_deadline(deadline, max_days_before=60)
            payment_created = self._random_dt_before_deadline(deadline, max_days_before=60)
            payment_updated = min(
                payment_created + timedelta(days=random.randint(0, 3), hours=random.randint(0, 12)),
                payment_created + timedelta(days=5),
            )
            Payment.objects.create(
                booking=booking,
                amount=total_cost,
                paid_at=paid_at,
                status=random.choice([Payment.PaymentStatus.PAID, Payment.PaymentStatus.PENDING]),
                created_at=payment_created,
                updated_at=payment_updated,
            )

    def _create_articles(self):
        base = datetime(2026, 5, 17, 12, 0, 0, tzinfo=dt_timezone.utc)
        Article.objects.bulk_create(
            [
                Article(
                    title="Открытие нового SPA-комплекса в отеле",
                    short_content="В нашем отеле начал работу обновленный SPA-комплекс с расширенной программой процедур.",
                    full_text=(
                        "Мы завершили модернизацию SPA-зоны: добавлены новые кабинеты массажа, "
                        "инфракрасная сауна и зона восстановления после перелета. Для гостей доступны "
                        "программы на 30, 60 и 90 минут, включая семейные пакеты выходного дня."
                    ),
                    image=None,
                    created_at=base - timedelta(days=46),
                    updated_at=base - timedelta(days=46),
                ),
                Article(
                    title="Запуск экспресс-регистрации при заезде",
                    short_content="Служба приема и размещения внедрила экспресс-регистрацию для гостей с онлайн-бронированием.",
                    full_text=(
                        "Новая процедура сокращает время оформления на стойке до 2-3 минут. "
                        "Гости заранее заполняют данные профиля в личном кабинете, после чего получают "
                        "готовый пакет документов и ключ-карту при прибытии."
                    ),
                    image=None,
                    created_at=base - timedelta(days=27),
                    updated_at=base - timedelta(days=20),
                ),
                Article(
                    title="Сезонное обновление меню завтраков",
                    short_content="Ресторан отеля представил новое сезонное меню завтраков из локальных продуктов.",
                    full_text=(
                        "В меню добавлены блюда белорусской и европейской кухни, отдельная линейка "
                        "для детей и гостей с особыми пищевыми предпочтениями. Также расширена карта "
                        "горячих напитков и введена станция свежевыжатых соков."
                    ),
                    image=None,
                    created_at=base - timedelta(days=7),
                    updated_at=base - timedelta(days=3),
                ),
            ]
        )

    def _create_banners(self):
        Banner.objects.all().delete()
        Banner.objects.bulk_create([
            Banner(title="Раннее бронирование −15%", image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=960&h=320&fit=crop", link_url="/rooms/", alt_text="Баннер: люкс со скидкой", sort_order=1, is_active=True),
            Banner(title="SPA и завтраки в подарок", image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=960&h=320&fit=crop", link_url="/extra-services/", alt_text="Баннер: SPA и завтраки", sort_order=2, is_active=True),
            Banner(title="Семейные номера", image_url="https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=960&h=320&fit=crop", link_url="", alt_text="Баннер: семейные номера", sort_order=3, is_active=True),
        ])

    def _create_partners(self):
        Partner.objects.all().delete()
        Partner.objects.bulk_create([
            Partner(name="Booking.com", logo_url="https://dummyimage.com/160x80/003580/fff&text=Booking", website_url="https://www.booking.com/", sort_order=1, is_active=True),
            Partner(name="Tripadvisor", logo_url="https://dummyimage.com/160x80/00aa6c/fff&text=TripAd", website_url="https://www.tripadvisor.com/", sort_order=2, is_active=True),
            Partner(name="Airbnb", logo_url="https://dummyimage.com/160x80/ff5a5f/fff&text=Airbnb", website_url="https://www.airbnb.com/", sort_order=3, is_active=True),
        ])

    def _create_company_info(self):
        CompanyInfo.objects.create(
            company_text=(
                "Гостиница 'Aurora Hotel' - городской четырехзвездочный отель, "
                "ориентированный на деловых и семейных гостей."
            ),
            history_by_years=(
                "2014 - запуск гостиницы; 2018 - расширение номерного фонда; "
                "2021 - цифровизация процессов бронирования; 2025 - обновление SPA и ресторана."
            ),
            company_details=(
                "ООО 'Аурора Хоспиталити', УНП 192345678, "
                "юридический адрес: г. Минск, ул. Примерная, 10."
            ),
        )

    def _create_glossary(self):
        Glossary.objects.bulk_create(
            [
                Glossary(
                    question="Что такое ранний заезд?",
                    answer=(
                        "Ранний заезд позволяет заселиться до стандартного времени при наличии "
                        "подготовленного номера и может тарифицироваться дополнительно."
                    ),
                ),
                Glossary(
                    question="Чем отличается тариф с завтраком?",
                    answer=(
                        "Тариф с завтраком включает утренний шведский стол в ресторане отеля "
                        "в рамках количества гостей по бронированию."
                    ),
                ),
                Glossary(
                    question="Можно ли отменить бронирование без штрафа?",
                    answer=(
                        "Да, при отмене в пределах срока бесплатной отмены, указанного в подтверждении "
                        "бронирования."
                    ),
                ),
                Glossary(
                    question="Как оформить трансфер из аэропорта?",
                    answer=(
                        "Трансфер можно заказать при бронировании номера или через администратора "
                        "не позднее чем за 12 часов до прибытия."
                    ),
                ),
                Glossary(
                    question="Разрешено ли проживание с детьми?",
                    answer=(
                        "Да, отель принимает гостей с детьми, а для семей доступны детские кроватки "
                        "и специальные предложения."
                    ),
                ),
            ]
        )

    def _create_vacancies(self):
        Vacancy.objects.bulk_create(
            [
                Vacancy(
                    title="Администратор службы приема и размещения",
                    description="Организация заезда и выезда гостей, работа с PMS-системой, решение запросов и координация служб.",
                    requirements="Опыт работы от 1 года, грамотная речь, английский Intermediate, стрессоустойчивость.",
                    salary_level="1500-1900 BYN + бонусы",
                ),
                Vacancy(
                    title="Горничная",
                    description="Поддержание стандартов чистоты в номерах и общественных зонах, пополнение расходных материалов.",
                    requirements="Аккуратность, ответственность, готовность к сменному графику.",
                    salary_level="1200-1500 BYN + премии",
                ),
                Vacancy(
                    title="Повар горячего цеха",
                    description="Приготовление блюд по технологическим картам, контроль качества и соблюдение санитарных требований.",
                    requirements="Профильное образование, опыт от 2 лет, знание HACCP.",
                    salary_level="1800-2400 BYN",
                ),
                Vacancy(
                    title="Менеджер по бронированию",
                    description="Обработка входящих запросов на бронирование, работа с онлайн-системами и поддержка гостей.",
                    requirements="Опыт в гостиничном бизнесе от 1 года, навыки работы с CRM, коммуникабельность.",
                    salary_level="1400-1700 BYN",
                ),
                Vacancy(
                    title="Бармен",
                    description="Обслуживание гостей в лобби-баре, приготовление напитков, поддержание чистоты бара.",
                    requirements="Опыт работы барменом от 1 года, знание карты коктейлей, работа в выходные.",
                    salary_level="1300-1600 BYN + чаевые",
                ),
                Vacancy(
                    title="Специалист по маркетингу",
                    description="Ведение соцсетей отеля, подготовка рекламных материалов, анализ рынка.",
                    requirements="Высшее образование, опыт в маркетинге от 2 лет, знание SMM-инструментов.",
                    salary_level="1600-2000 BYN",
                ),
                Vacancy(
                    title="Инженер-электрик",
                    description="Обслуживание электрооборудования отеля, оперативное устранение неисправностей.",
                    requirements="Профильное образование, допуск к работе с электроустановками, опыт от 3 лет.",
                    salary_level="1500-1900 BYN",
                ),
                Vacancy(
                    title="Консьерж",
                    description="Встреча и сопровождение гостей, помощь с багажом, заказ такси и экскурсий.",
                    requirements="Презентабельная внешность, знание английского языка, стрессоустойчивость.",
                    salary_level="1100-1400 BYN + чаевые",
                ),
                Vacancy(
                    title="Бухгалтер",
                    description="Ведение бухгалтерского учета отеля, расчет зарплаты, отчетность в ФСЗН.",
                    requirements="Высшее экономическое образование, опыт от 3 лет, знание 1С.",
                    salary_level="1700-2200 BYN",
                ),
                Vacancy(
                    title="Руководитель отдела продаж",
                    description="Развитие корпоративных продаж, проведение переговоров, выполнение KPI отдела.",
                    requirements="Опыт в продажах от 3 лет, управленческие навыки, английский Upper-Intermediate.",
                    salary_level="2200-3000 BYN + бонусы",
                ),
            ]
        )

    def _create_reviews(self):
        base = datetime(2026, 5, 17, 12, 0, 0, tzinfo=dt_timezone.utc)
        Review.objects.bulk_create(
            [
                Review(
                    author_name="Марина К.", rating=5,
                    review_text="Понравился внимательный персонал и быстрый check-in, номер был идеально подготовлен.",
                    created_at=base - timedelta(days=45), updated_at=base - timedelta(days=45),
                ),
                Review(
                    author_name="Олег Н.", rating=4,
                    review_text="Удобное расположение и отличный завтрак, хотелось бы чуть больше парковочных мест.",
                    created_at=base - timedelta(days=40), updated_at=base - timedelta(days=40),
                ),
                Review(
                    author_name="Светлана П.", rating=5,
                    review_text="Останавливаемся семьей второй раз, сервис стабильно высокий и детям комфортно.",
                    created_at=base - timedelta(days=35), updated_at=base - timedelta(days=35),
                ),
                Review(
                    author_name="Дмитрий Л.", rating=3,
                    review_text="Номер чистый, но шумно от лифта. В целом неплохо для своей цены.",
                    created_at=base - timedelta(days=30), updated_at=base - timedelta(days=30),
                ),
                Review(
                    author_name="Елена С.", rating=4,
                    review_text="Приветливый персонал на ресепшн, вкусные завтраки, удобная парковка.",
                    created_at=base - timedelta(days=25), updated_at=base - timedelta(days=25),
                ),
                Review(
                    author_name="Алексей В.", rating=5,
                    review_text="Отличный отель для командировки, всё необходимое есть, тихо и комфортно.",
                    created_at=base - timedelta(days=20), updated_at=base - timedelta(days=20),
                ),
                Review(
                    author_name="Татьяна М.", rating=4,
                    review_text="Хорошее расположение в центре, рядом магазины и кафе. Номер просторный.",
                    created_at=base - timedelta(days=16), updated_at=base - timedelta(days=16),
                ),
                Review(
                    author_name="Иван Г.", rating=2,
                    review_text="Завтрак однообразный, кондиционер в номере работал с перебоями.",
                    created_at=base - timedelta(days=12), updated_at=base - timedelta(days=12),
                ),
                Review(
                    author_name="Надежда К.", rating=5,
                    review_text="Спа-зона превзошла ожидания, обязательно вернёмся снова!",
                    created_at=base - timedelta(days=6), updated_at=base - timedelta(days=6),
                ),
                Review(
                    author_name="Павел Р.", rating=4,
                    review_text="Чисто, уютно, персонал отзывчивый. Рекомендую для семейного отдыха.",
                    created_at=base - timedelta(days=2), updated_at=base - timedelta(days=2),
                ),
            ]
        )

    def _create_promocodes(self):
        PromoCode.objects.bulk_create(
            [
                PromoCode(code="SUMMER10", discount_percent=Decimal("10.00"), status=PromoCode.PromoStatus.ACTIVE),
                PromoCode(code="WEEKEND15", discount_percent=Decimal("15.00"), status=PromoCode.PromoStatus.ACTIVE),
                PromoCode(code="SPRING20", discount_percent=Decimal("20.00"), status=PromoCode.PromoStatus.ACTIVE),
                PromoCode(code="LOYAL5", discount_percent=Decimal("5.00"), status=PromoCode.PromoStatus.ACTIVE),
                PromoCode(code="HOLIDAY25", discount_percent=Decimal("25.00"), status=PromoCode.PromoStatus.ACTIVE),
                PromoCode(code="ARCHIVE20", discount_percent=Decimal("20.00"), status=PromoCode.PromoStatus.ARCHIVED),
                PromoCode(code="ARCHIVE15", discount_percent=Decimal("15.00"), status=PromoCode.PromoStatus.ARCHIVED),
                PromoCode(code="ARCHIVE10", discount_percent=Decimal("10.00"), status=PromoCode.PromoStatus.ARCHIVED),
                PromoCode(code="NEWYEAR30", discount_percent=Decimal("30.00"), status=PromoCode.PromoStatus.ARCHIVED),
                PromoCode(code="WINTER15", discount_percent=Decimal("15.00"), status=PromoCode.PromoStatus.ARCHIVED),
            ]
        )
