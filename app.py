import os
from datetime import date
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from services.sheets import InventoryService

app = FastAPI(title="Mini Inventory Management System")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "inventory-secret-key"),
    max_age=86400,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
inventory_service = InventoryService()


def require_authentication(request: Request) -> Response | None:
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/", response_class=HTMLResponse)
async def process_login(request: Request, password: str = Form(...)) -> Response:
    if password == "123456789":
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid Password"})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    redirect = require_authentication(request)
    if redirect is not None:
        return redirect

    month_summary = inventory_service.get_month_summary()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "sheet_status": inventory_service.status_message,
            "month_summary": month_summary,
        },
    )


@app.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/purchase", response_class=HTMLResponse)
async def purchase_page(request: Request) -> Response:
    redirect = require_authentication(request)
    if redirect is not None:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="purchase.html",
        context={
            "products": inventory_service.product_names,
            "today": date.today().isoformat(),
            "form_data": None,
            "message": None,
            "message_type": None,
            "sheet_status": inventory_service.status_message,
        },
    )


@app.post("/purchase", response_class=HTMLResponse)
async def save_purchase(
    request: Request,
    product: str = Form(...),
    weight: str = Form(...),
    quantity: str = Form(...),
    purchase_rate: str = Form(...),
    supplier_name: str = Form(...),
    date_value: str | None = Form(None),
    submitted_date_field: str | None = Form(None),
    notes: str = Form(""),
) -> Response:
    redirect = require_authentication(request)
    if redirect is not None:
        return redirect

    submitted_date = date_value or submitted_date_field or date.today().isoformat()

    form_data: dict[str, Any] = {
        "product": product,
        "weight": weight,
        "quantity": quantity,
        "purchase_rate": purchase_rate,
        "supplier_name": supplier_name,
        "date": submitted_date,
        "notes": notes,
    }

    try:
        inventory_service.add_purchase(
            {
                "date": form_data["date"],
                "product": form_data["product"],
                "weight": float(weight),
                "quantity": int(quantity),
                "purchase_rate": float(purchase_rate),
                "supplier": supplier_name,
                "notes": notes,
            }
        )
    except (TypeError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="purchase.html",
            context={
                "products": inventory_service.product_names,
                "today": date.today().isoformat(),
                "form_data": form_data,
                "message": f"Please check the input values: {exc}",
                "message_type": "error",
                "sheet_status": inventory_service.status_message,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="purchase.html",
        context={
            "products": inventory_service.product_names,
            "today": date.today().isoformat(),
            "form_data": None,
            "message": "Purchase saved successfully.",
            "message_type": "success",
            "sheet_status": inventory_service.status_message,
        },
    )


@app.get("/stock/{product_name}")
async def get_stock(product_name: str) -> JSONResponse:
    available_stock = inventory_service.get_available_stock(product_name)
    return JSONResponse({"product": product_name, "available_stock": available_stock})


@app.get("/sale", response_class=HTMLResponse)
async def sale_page(request: Request) -> Response:
    redirect = require_authentication(request)
    if redirect is not None:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="sale.html",
        context={
            "products": inventory_service.product_names,
            "today": date.today().isoformat(),
            "form_data": None,
            "message": None,
            "message_type": None,
            "available_stock": None,
            "sheet_status": inventory_service.status_message,
        },
    )


@app.post("/sale", response_class=HTMLResponse)
async def save_sale(
    request: Request,
    product: str = Form(...),
    sale_rate: str = Form(...),
    quantity: str = Form(...),
    customer_name: str = Form(...),
    date_value: str | None = Form(None),
    submitted_date_field: str | None = Form(None),
    notes: str = Form(""),
) -> Response:
    redirect = require_authentication(request)
    if redirect is not None:
        return redirect

    submitted_date = date_value or submitted_date_field or date.today().isoformat()

    form_data: dict[str, Any] = {
        "product": product,
        "sale_rate": sale_rate,
        "quantity": quantity,
        "customer_name": customer_name,
        "date": submitted_date,
        "notes": notes,
    }

    try:
        available_stock = inventory_service.get_available_stock(product)
        sale_quantity = int(quantity)
    except (TypeError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="sale.html",
            context={
                "products": inventory_service.product_names,
                "today": date.today().isoformat(),
                "form_data": form_data,
                "message": f"Please check the input values: {exc}",
                "message_type": "error",
                "available_stock": None,
                "sheet_status": inventory_service.status_message,
            },
        )

    if sale_quantity > available_stock:
        return templates.TemplateResponse(
            request=request,
            name="sale.html",
            context={
                "products": inventory_service.product_names,
                "today": date.today().isoformat(),
                "form_data": form_data,
                "message": "Insufficient Stock",
                "message_type": "error",
                "available_stock": available_stock,
                "sheet_status": inventory_service.status_message,
            },
        )

    inventory_service.add_sale(
        {
            "date": form_data["date"],
            "product": form_data["product"],
            "quantity": sale_quantity,
            "sale_rate": float(sale_rate),
            "customer": customer_name,
            "notes": notes,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="sale.html",
        context={
            "products": inventory_service.product_names,
            "today": date.today().isoformat(),
            "form_data": None,
            "message": "Sale saved successfully.",
            "message_type": "success",
            "available_stock": inventory_service.get_available_stock(product),
            "sheet_status": inventory_service.status_message,
        },
    )
