from django.shortcuts import render, redirect
from django.http import JsonResponse,HttpResponse
from .models import Banner,Category,Brand,Product,ProductAttribute, CartOrder, CartOrderItems,ProductReview, MotherboardAPI
from django.db.models import Max,Min,Count
from django.template.loader import render_to_string
from .forms import SignupForm, ReviewAdd
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
#paypal
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from paypal.standard.forms import PayPalPaymentsForm

import requests


# home page
def home(request):
	banners=Banner.objects.all().order_by('-id')
	data=Product.objects.filter(is_featured=True).order_by('-id')
	return render(request,'index.html',{'data':data, 'banners':banners})

# Category
def category_list(request):
	data=Category.objects.all().order_by('-id')
	return render(request,'category_list.html', {'data':data})

# Brand
def brand_list(request):
	data=Brand.objects.all().order_by('-id')
 
	mother = MotherboardAPI.objects.all()
 
	context = {
		"mother" : mother,
  		'data':data
	}
	return render(request,'brand_list.html', context)

# Product List
def product_list(request):
	total_data=Product.objects.count()
	data=Product.objects.all().order_by('-id')[:3]
	
	return render(request,'product_list.html', 
		{
			'data':data,
			'total_data' : total_data,
			
		})


# Product List berdasar kategori
def category_product_list(request,cat_id):
	category=Category.objects.get(id=cat_id)
	data=Product.objects.filter(category=category).order_by('-id')

	return render(request,'category_product_list.html', 
		{
			'data':data,

		})

# Product List berdasar brand
def brand_product_list(request,brand_id):
	brand=Brand.objects.get(id=brand_id)
	data=Product.objects.filter(brand=brand).order_by('-id')

	return render(request,'category_product_list.html', 
		{
			'data':data,
			#'cats':cats,
			#'brands':brands,
			#'colors':colors,
			#'sizes':sizes,
		})

# Product detail
def product_detail (request,slug,id):
	product=Product.objects.get(id=id)
	related_products=Product.objects.filter(category=product.category).exclude(id=id)[:3]
	colors=ProductAttribute.objects.filter(product=product).values('color__id','color__title','color__color_code').distinct()
	sizes=ProductAttribute.objects.filter(product=product).values('size__id','size__title','price','color__id').distinct()
	reviewForm=ReviewAdd()

	#check
	canAdd=True
	reviewCheck=ProductReview.objects.filter(user=request.user,product=product).count()
	#end

	return render (request, 'product_detail.html', {'data':product, 'related':related_products, 'colors':colors, 'sizes':sizes, 'form':reviewForm})

# Search
def search(request):
	q=request.GET['q']
	data=Product.objects.filter(title__icontains=q).order_by('-id')
	return render(request,'search.html',{'data':data})

# Filter Data
def filter_data(request):
	colors=request.GET.getlist('color[]')
	categories=request.GET.getlist('category[]')
	brands=request.GET.getlist('brand[]')
	sizes=request.GET.getlist('size[]')
	minPrice=request.GET['minPrice']
	maxPrice=request.GET['maxPrice']
	allProducts=Product.objects.all().order_by('-id').distinct()
	allProducts=allProducts.filter(productattribute__price__gte=minPrice)
	allProducts=allProducts.filter(productattribute__price__lte=maxPrice)

	if len(colors)>0:
		allProducts=allProducts.filter(productattribute__color__id__in=colors).distinct()
	if len(categories)>0:
		allProducts=allProducts.filter(category__id__in=categories).distinct()
	if len(brands)>0:
		allProducts=allProducts.filter(brand__id__in=brands).distinct()
	if len(sizes)>0:
		allProducts=allProducts.filter(productattribute__size__id__in=sizes).distinct()

	t=render_to_string('ajax/product-list.html',{'data':allProducts})
	return JsonResponse({'data':t})
#    return JsonResponse({'data':allProducts})

# Load More
def load_more_data(request):
	offset=int(request.GET['offset'])
	limit=int(request.GET['limit'])
	data=Product.objects.all().order_by('-id')[offset:offset+limit]
	
	t=render_to_string('ajax/product-list.html',{'data':data})
	return JsonResponse({'data':t})

# Add to cart
def add_to_cart(request):
	cart_p={}
	cart_p[str(request.GET['id'])]={
		'image':request.GET['image'],
		'title':request.GET['title'],
		'qty':request.GET['qty'],
		'price':request.GET['price'],
	}
	if 'cartdata' in request.session:
		if str(request.GET['id']) in request.session['cartdata']:
			cart_data=request.session['cartdata']
			cart_data[str(request.GET['id'])]['qty'] = int(cart_p[str(request.GET['id'])]['qty'])
			cart_data.update(cart_data)
			request.session['cartdata']=cart_data
		else:
			cart_data=request.session['cartdata']
			cart_data.update(cart_data)
			request.session['cartdata']=cart_data
	else:
		request.session['cartdata']=cart_p
	return JsonResponse({'data':request.session['cartdata'],'totalitems':len(request.session['cartdata'])})



# Cart List Page
def cart_list(request):
	total_amt=0
	if 'cartdata' in request.session:
		for p_id,item in request.session['cartdata'].items():
			total_amt+=int(item['qty'])*float(item['price'])
		return render(request, 'cart.html',{'cart_data':request.session['cartdata'],'totalitems':len(request.session['cartdata']),'total_amt':total_amt})
	else:
		return render(request, 'cart.html',{'cart_data':'','totalitems':0,'total_amt':total_amt})

# Delete Cart Item
def delete_cart_item(request):
	p_id=str(request.GET['id'])
	if 'cartdata' in request.session:
		if p_id in request.session['cartdata']:
			cart_data=request.session['cartdata']
			del request.session['cartdata'][p_id]
			request.session['cartdata']=cart_data
	total_amt=0 
	for p_id, item in request.session['cartdata'].items():
		total_amt+=int(item['qty'])*float(item['price'])
	t=render_to_string('ajax/cart-list.html',{'cart_data':request.session['cartdata'],'totalitems':len(request.session['cartdata']), 'total_amt':total_amt})
	return JsonResponse({'data':t, 'totalitems':len(request.session['cartdata'])})

# Update Cart Item
def update_cart_item(request):
	p_id=str(request.GET['id'])
	p_qty=request.GET['qty']
	if 'cartdata' in request.session:
		if p_id in request.session['cartdata']:
			cart_data=request.session['cartdata']
			cart_data[str(request.GET['id'])]['qty'] = p_qty
			request.session['cartdata']=cart_data
	total_amt=0 
	for p_id, item in request.session['cartdata'].items():
		total_amt+=int(item['qty'])*float(item['price'])
	t=render_to_string('ajax/cart-list.html',{'cart_data':request.session['cartdata'],'totalitems':len(request.session['cartdata']), 'total_amt':total_amt})
	return JsonResponse({'data':t, 'totalitems':len(request.session['cartdata'])})

# Sign Up
def signup(request):
	if request.method=='POST':
		form=SignupForm(request.POST)
		if form.is_valid():
			form.save()
			username=form.cleaned_data.get('username')
			pwd=form.cleaned_data.get('password1')
			user=authenticate(username=username,password=pwd)
			login(request, user)
			return redirect('home')
	form=SignupForm
	return render(request, 'registration/signup.html',{'form':form})


# Checkout
@login_required
def checkout(request):

	total_amt=0
	totalAmt=0
	if 'cartdata' in request.session:
		for p_id,item in request.session['cartdata'].items():
			totalAmt+=int(item['qty'])*float(item['price'])
		# order
		order=CartOrder.objects.create(
			user=request.user,
			total_amt=totalAmt
		)
		# end
		for p_id,item in request.session['cartdata'].items():
			total_amt+=int(item['qty'])*float(item['price'])
			# order items
			items=CartOrderItems.objects.create (
				order=order,
				invoice_no='INV-'+str(order.id),
				item=item['title'],
				image=item['image'],
				qty=item['qty'],
				price=item['price'],
				total=float(item['qty'])*float(item['price'])
			)
			# end
		# rocess payment
		host = request.get_host()
		paypal_dict = {
			'business': settings.PAYPAL_RECEIVER_EMAIL,
			'amount': total_amt,
			'item_name': 'OrderNo-'+str(order.id),
			'invoice': 'INV-'+str(order.id),
			'currency_code': 'USD',
			'notify_url': 'http://{}{}'.format(host,reverse('paypal-ipn')),
			'return_url': 'http://{}{}'.format(host,reverse('payment_done')),
			'cancel_return': 'http://{}{}'.format(host,reverse('payment_cancelled')),
		}
		form = PayPalPaymentsForm(initial=paypal_dict)
		return render(request, 'checkout.html',{'cart_data':request.session['cartdata'],
		'totalitems':len(request.session['cartdata']),'total_amt':total_amt, 'form':form})

@csrf_exempt
def payment_done(request):
	returnData=request.POST
	return render(request, 'payment-success.html',{'data':returnData})


@csrf_exempt
def payment_canceled(request):
	return render(request, 'payment-fail.html')

# save review
def save_review(request,pid):
	product=Product.objects.get(pk=pid)
	user=request.user
	review=ProductReview.objects.create(
		user=user,
		product=product,
		review_text=request.POST['review_text'],
		review_rating=request.POST['review_rating'],
		)
	return JsonResponse({'bool':True})

# User Dashboard
def my_dashboard(request):
	return render (request, 'user/dashboard.html')

#API
def sinkron_api(request):
    
	url = "https://computer-components-api.p.rapidapi.com/motherboard"
	querystring = {"limit":"10","offset":"0"}
	headers = {
		"X-RapidAPI-Key": "ba85849e35mshaa72c68ccba2d83p1e92f0jsn6969919cf633",
		"X-RapidAPI-Host": "computer-components-api.p.rapidapi.com"
	}
	response = requests.request("GET", url, headers=headers, params=querystring)

	data = response.json()
	
	for d in data:
		cek_mother = MotherboardAPI.objects.filter(id_mother=d['id'])
		if cek_mother.exists():
			mother = cek_mother.first()
			mother.id_mother = d['id']
			mother.title = d['title']
			mother.link_olshop = d['link']
			mother.img = d['img']
			mother.brandme = d['brand']
			mother.modelme = d['model']
			mother.formFactor = d['formFactor']
			mother.chipset = d['chipset']
			mother.memorySlots = d['memorySlots']
			mother.socketType = d['socketType']
			mother.save()
		else:
			MotherboardAPI.objects.create(
				id_mother = d['id'],
				title = d['title'],
				link_olshop = d['link'],
				img = d['img'],
				brandme = d['brand'],
				modelme = d['model'],
				formFactor = d['formFactor'],
				chipset = d['chipset'],
				memorySlots = d['memorySlots'],
				socketType = d['socketType']
			)
	return HttpResponse("<h1>Berhasil connect API</h1>")
 
