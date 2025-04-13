module m
implicit none
contains
function mean(x) result(xmean)
real, intent(in) :: x(:)
real             :: xmean
integer          :: i, n
real             :: xsum
xsum = 0.0
n = size(x)
do i=1,n
   xsum = xsum + x(i)
end do
xmean = xsum/n
end function mean
end module m

program main
use m, only: mean
implicit none
integer, parameter :: n = 3
real :: x(n)
integer :: i
x(1) = 10.0
x(2) = 20.0
x(3) = 30.0
do i=1,n
   print*,i,10*x(i)
end do
print*,mean(x)
end program main
