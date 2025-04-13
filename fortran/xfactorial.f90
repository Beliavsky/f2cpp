! demonstrate function, array constructor, and
! looping over array elements
module m
implicit none
contains
function factorial(n) result(nfac)
integer, intent(in) :: n
integer :: nfac
integer :: i
nfac = 1
do i=2,n
   nfac = nfac*i
end do
end function factorial
end module m

program main
use m
implicit none
integer, parameter :: n = 3, vec(n) = [3, 5, 10]
integer :: i, fac
real :: xfac
do i=1,n
   fac = factorial(vec(i))
   xfac = fac
   print*,vec(i), fac, sqrt(xfac)
   if (fac > 100) exit
end do
end program main
