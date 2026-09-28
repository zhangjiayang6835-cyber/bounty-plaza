#include "sfp_load_macro.h"
#include <assert.h>

int main() {
    assert(sfp_load_macro(5) == 5);
    assert(sfp_load_macro(-3) == -3);
    assert(sfp_load_macro(0) == 0);
    return 0;
}
