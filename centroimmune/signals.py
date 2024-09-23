from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cita, Factura

@receiver(post_save, sender=Cita)
def crear_factura_al_crear_cita(sender, instance, created, **kwargs):
    if created and instance.tratamiento:
        Factura.objects.create(
            paciente=instance.paciente,
            cita=instance,
            monto=instance.tratamiento.costo,
            descripcion=f"Factura generada automáticamente para la cita el {instance.fecha.strftime('%d/%m/%Y %H:%M')}"
        )
