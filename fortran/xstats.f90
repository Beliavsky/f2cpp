module m
implicit none
contains
function mean(x) result(xmean)
real, intent(in)  :: x(:)
real              :: xmean
real              :: xsum
integer           :: i, n
n = size(x)
xsum = 0.0
do i=1,n
   xsum = xsum + x(i)
end do
xmean = xsum/n
end function mean
end module m

program main
use m
real :: x(3)
x = [10.0, 20.0, 90.0]
print*,mean(x)
end program main
