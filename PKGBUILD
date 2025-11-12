# Maintainer: Saeed Badrelden <helwanlinux@gmail.com.com>
pkgname=momo
pkgver=1.0.0
pkgrel=1
pkgdesc="Momo - Helwan Linux Diagnostics Tool (TUI + Streaming + Dynamic Disks)"
arch=('x86_64')
url="https://github.com/helwan-linux/momo"
license=('GPL')
depends=('python' 'python-curses' 'lm_sensors' 'smartmontools' 'hdparm' 'nvme-cli' 'stress-ng' 'memtester' 'sysbench')
# المصدر هو "momo" (اسم ملف الكود التنفيذي).
source=("momo")
# هام جداً: يجب حساب التجزئة (Hash) الحقيقي لملف الكود momo واستبدال 'SKIP' به
sha256sums=('3205c66885d23dfc6f9688c93fdc51e0dfcec3fa6ecd6359cb21cad6e4a0dda8') 

package() {
    # هذا هو التعديل الهام: التثبيت في المسار القياسي لحزم Arch وهو /usr/bin
    install -Dm755 "${srcdir}/momo" "${pkgdir}/usr/bin/momo"
}
