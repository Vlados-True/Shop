from decimal import Decimal
import stripe
from django.conf import settings
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from orders.models import Order

# создать экземпляр Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


def payment_process(request):
    order_id = request.session.get('order_id', None)
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        success_url = request.build_absolute_uri(
            reverse('payment:completed'))
        cancel_url = request.build_absolute_uri(
            reverse('payment:canceled'))
        # данные сеанса оформления платежа Stripe
        session_data = {
            'mode': 'payment',
            'client_reference_id': order.id,
            'success_url': success_url,
            'cancel_url': cancel_url,
            'line_items': []
        }
        # добавить товарные позиции заказа
        # в сеанс оформления платежа Stripe
        for item in order.items.all():
            session_data['line_items'].append({
                'price_data': {
                    'unit_amount': int(item.price * Decimal('100')),
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name,
                    },
                },
                'quantity': item.quantity,
            })
        # купон Stripe
        if order.coupon:
            stripe_coupon = stripe.Coupon.create(
                name=order.coupon.code,
                percent_off=order.discount,
                duration='once')
            session_data['discounts'] = [{
                'coupon': stripe_coupon.id
            }]
            # создать сеанс оформления платежа Stripe
            session = stripe.checkout.Session.create(**session_data)
            # перенаправить к форме для платежа Stripe
            return redirect(session.url, code=303)
        else:
            return render(request, 'payment/process.html', locals())
        # создать сеанс оформления платежа Stripe
        session = stripe.checkout.Session.create(**session_data)
        # перенаправить к платежной форме Stripe
        return redirect(session.url, code=303)
    else:
        return render(request, 'payment/process.html', locals())


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')


"""
Представление payment_process выполняет следующую работу.
1. Текущий объект Order извлекается по сеансовому ключу order_id, который ранее был сохранен в сеансе представлением order_create.
2. Объект Order извлекается из базы данных по данному order_id. Если при
использовании функции сокращенного доступа get_object_ or_404()
возникает исключение Http404 (страница не найдена), то заказ с заданным ИД не найден.
3. Если представление загружается с по мощью запроса методом GET, то
прорисовывается и  возвращается шаблон payment/process.html. Этот
шаблон будет содержать сводную информацию о заказе и кнопку для
перехода к платежу, которая будет генерировать запрос методом POST
к представлению.
4. Если представление загружается с по мощью запроса методом POST, то
сеанс Stripe оформления платежа создается с использованием Stripe.
checkout.Session.create() со следующими ниже параметрами:
– mode: режим сеанса оформления платежа. Здесь используется значение payment, указывающее на разовый платеж. На странице https://
stripe.com/docs/api/checkout/sessions/object#checkout_session_objectmode можно увидеть другие принятые для этого параметра значения;
– client_reference_id: уникальная ссылка для этого платежа. Она будет
использоваться для согласования сеанса оформления платежа Stripe
с заказом. Передавая ИД заказа, платежи Stripe связываются с зака-
зами в вашей системе, и вы сможете получать уведомления от Stripe
о платежах, чтобы помечать заказы как оплаченные;
– success_url: URL-адрес, на который Stripe перенаправляет пользователя в  случае успешного платежа. Здесь используется request.
build_absolute_uri(), чтобы формировать абсолютный URI-иден тифи катор из пути URL-адреса. Документация по этому методу находится по адресу https://docs.djangoproject.com/en/4.1/ref/requestresponse/#django.http.HttpRequest.build_absolute_uri;
– cancel_url: URL-адрес, на который Stripe перенаправляет пользователя в случае отмены платежа;
– line_items: это пустой список. Далее он будет заполнен приобретаемыми товарными позициями заказа.
5. После создания сеанса оформления платежа возвращается HTTPперенаправление с кодом состояния, равным 303, чтобы перенаправить
пользователя к  Stripe. Код состояния 303 рекомендуется для перенаправления веб-приложений на новый URI-идентификатор после выполнения HTTP-запроса методом POST.

"""
